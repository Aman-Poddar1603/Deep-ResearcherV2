"""
SearchEngine.py — Deep Researcher v2
======================================
Parallel search across all (or targeted) ChromaDB collections.

  Agent Query
      │
      ▼
  SearchEngine.search(query, collections=["websites","pdfs","images"])
      │
      ├── asyncio.gather ──► query("websites")
      │                  ──► query("pdfs")
      │                  ──► query("images")
      │
      ▼
  _merge_results()  →  deduplicate + score-sort
      │
      ▼
  MergedContext  { results: [...], sources: [...], total: N }

Usage
-----
::

    from main.src.store.SearchEngine import search_engine

    context = await search_engine.search(
        query="transformer attention mechanism",
        collections=["websites", "pdfs"],
        n_results=5,
    )
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from main.src.utils.DRLogger import dr_logger, LogType
from main.src.utils.versionManagement import getAppVersion
from main.src.store.DBVector import db_vector_manager, metadata_store, COLLECTIONS

_std_logger = logging.getLogger(__name__)

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_MODEL = "embeddinggemma:latest"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _log(level: LogType, message: str, urgency: str = "none") -> None:
    getattr(_std_logger, level if level in ("info", "warning", "error") else "info")(
        message
    )
    try:
        dr_logger.log(
            log_type=level,
            message=message,
            origin="system",
            module="SEARCH",
            urgency=urgency,
            app_version=getAppVersion(),
        )
    except Exception as exc:
        _std_logger.error(f"DRLogger failure: {exc}")


# ---------------------------------------------------------------------------
# Query embedding helper (single text → vector)
# ---------------------------------------------------------------------------


async def _embed_query(text: str) -> Optional[List[float]]:
    """Embed a single query string via Ollama."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_EMBED_URL,
                json={"model": OLLAMA_MODEL, "prompt": text},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["embedding"]
    except Exception as exc:
        _log("error", f"Query embedding failed: {exc}", "moderate")
        return None


# ---------------------------------------------------------------------------
# Result structures
# ---------------------------------------------------------------------------


class SearchResult:
    """Single ranked result from one collection."""

    __slots__ = ("id", "document", "metadata", "distance", "collection")

    def __init__(
        self,
        id: str,
        document: Optional[str],
        metadata: Optional[Dict[str, Any]],
        distance: float,
        collection: str,
    ) -> None:
        self.id = id
        self.document = document
        self.metadata = metadata or {}
        self.distance = distance
        self.collection = collection

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "document": self.document,
            "metadata": self.metadata,
            "distance": self.distance,
            "collection": self.collection,
        }

    def __repr__(self) -> str:
        return f"<SearchResult id={self.id} dist={self.distance:.4f} col={self.collection}>"


class MergedContext:
    """
    Aggregated, deduplicated, score-sorted results from all queried collections.

    Attributes
    ----------
    results  : ranked list of SearchResult objects (best first)
    sources  : unique source URIs found across results
    total    : total result count before any final re-ranking trim
    query    : the original query string
    """

    def __init__(
        self,
        results: List[SearchResult],
        query: str,
    ) -> None:
        self.results = results
        self.query = query
        self.sources = list(
            {r.metadata.get("source", "") for r in results if r.metadata.get("source")}
        )
        self.total = len(results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total": self.total,
            "sources": self.sources,
            "results": [r.to_dict() for r in self.results],
        }

    def context_text(self, max_chars: int = 8000) -> str:
        """
        Concatenate document text for prompt injection.
        Stops before exceeding ``max_chars`` to respect context windows.
        """
        parts, total = [], 0
        for r in self.results:
            doc = r.document or ""
            if total + len(doc) > max_chars:
                break
            parts.append(
                f"[{r.collection.upper()} | {r.metadata.get('source','?')}]\n{doc}"
            )
            total += len(doc)
        return "\n\n---\n\n".join(parts)


# ===========================================================================
# SearchEngine
# ===========================================================================


class SearchEngine:
    """
    Parallel multi-collection semantic search engine.

    Methods
    -------
    search(query, collections, n_results, metadata_filter)
        Main entry point. Embeds query, fans out to all requested collections
        concurrently via asyncio.gather, merges and returns a MergedContext.

    search_image(embedding, collections, n_results)
        Search with a pre-computed image embedding (from SigLIPEmbedder).

    collection_search(query, collection_name, n_results, metadata_filter)
        Single-collection targeted search. Returns raw ChromaDB result dict.
    """

    # ------------------------------------------------------------------
    # Primary search entry point
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        collections: Optional[List[str]] = None,
        n_results: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        top_k: int = 20,
    ) -> MergedContext:
        """
        Embed ``query``, then concurrently search all (or specified) collections.

        Parameters
        ----------
        query           : Natural language query string.
        collections     : Subset of COLLECTIONS to search. Defaults to all four.
        n_results       : Results per collection.
        metadata_filter : ChromaDB ``where`` clause applied to every collection.
        top_k           : Final cap on merged results (after dedup + sort).

        Returns
        -------
        MergedContext
        """
        target_cols = self._validate_collections(collections)
        _log("info", f"search() query='{query[:80]}' cols={target_cols} k={n_results}")

        embedding = await _embed_query(query)
        if embedding is None:
            _log("error", "Cannot search — query embedding returned None.", "moderate")
            return MergedContext(results=[], query=query)

        return await self._fan_out_search(
            query=query,
            embedding=embedding,
            collections=target_cols,
            n_results=n_results,
            metadata_filter=metadata_filter,
            top_k=top_k,
        )

    async def search_image(
        self,
        embedding: List[float],
        collections: Optional[List[str]] = None,
        n_results: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
        top_k: int = 20,
    ) -> MergedContext:
        """
        Search using a pre-computed image embedding (e.g. from SigLIPEmbedder).
        Useful for cross-modal retrieval.
        """
        target_cols = self._validate_collections(collections or ["images"])
        _log("info", f"search_image() cols={target_cols} k={n_results}")

        return await self._fan_out_search(
            query="<image query>",
            embedding=embedding,
            collections=target_cols,
            n_results=n_results,
            metadata_filter=metadata_filter,
            top_k=top_k,
        )

    async def collection_search(
        self,
        query: str,
        collection_name: str,
        n_results: int = 10,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Single-collection targeted search. Returns raw ChromaDB result dict
        (useful when callers need unmerged, unprocessed hits).
        """
        embedding = await _embed_query(query)
        if embedding is None:
            return {"success": False, "message": "Embedding failed.", "data": None}

        return await db_vector_manager.query(
            collection_name=collection_name,
            query_embeddings=[embedding],
            n_results=n_results,
            where=metadata_filter,
        )

    # ------------------------------------------------------------------
    # Internal fan-out + merge
    # ------------------------------------------------------------------

    async def _fan_out_search(
        self,
        query: str,
        embedding: List[float],
        collections: List[str],
        n_results: int,
        metadata_filter: Optional[Dict[str, Any]],
        top_k: int,
    ) -> MergedContext:
        """Concurrently query all target collections and merge results."""

        async def _single_search(col: str) -> List[SearchResult]:
            result = (
                await db_vector_manager.query(
                    collection_name=collection_name,
                    query_embeddings=[embedding],
                    n_results=n_results,
                    where=metadata_filter,
                )
                if False
                else await db_vector_manager.query(  # unified call
                    collection_name=col,
                    query_embeddings=[embedding],
                    n_results=n_results,
                    where=metadata_filter,
                )
            )

            hits: List[SearchResult] = []
            if not result.get("success"):
                _log(
                    "warning",
                    f"Collection '{col}' returned no results: {result.get('message')}",
                )
                return hits

            data = result.get("data", {})
            ids = (data.get("ids") or [[]])[0]
            docs = (data.get("documents") or [[]])[0]
            metas = (data.get("metadatas") or [[]])[0]
            distances = (data.get("distances") or [[]])[0]

            for id_, doc, meta, dist in zip(
                ids, docs, metas or [{}] * len(ids), distances
            ):
                hits.append(
                    SearchResult(
                        id=id_,
                        document=doc,
                        metadata=meta,
                        distance=float(dist),
                        collection=col,
                    )
                )
            return hits

        # Fan out
        per_collection: List[List[SearchResult]] = await asyncio.gather(
            *[_single_search(c) for c in collections],
            return_exceptions=False,
        )

        merged = self._merge_results(per_collection, top_k=top_k)
        _log(
            "success",
            f"search() merged {len(merged)} results across {len(collections)} collection(s).",
        )
        return MergedContext(results=merged, query=query)

    @staticmethod
    def _merge_results(
        per_collection: List[List[SearchResult]],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Deduplicate (by document ID) and sort by ascending distance (lower = better).
        """
        seen: Dict[str, SearchResult] = {}
        for results in per_collection:
            for r in results:
                if r.id not in seen or r.distance < seen[r.id].distance:
                    seen[r.id] = r

        sorted_results = sorted(seen.values(), key=lambda r: r.distance)
        return sorted_results[:top_k]

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_collections(collections: Optional[List[str]]) -> List[str]:
        if not collections:
            return list(COLLECTIONS)
        invalid = [c for c in collections if c not in COLLECTIONS]
        if invalid:
            raise ValueError(f"Unknown collections: {invalid}. Valid: {COLLECTIONS}")
        return collections

    async def health(self) -> Dict[str, Any]:
        """Quick health-check across all collections."""
        return await db_vector_manager.all_collection_health()


# ===========================================================================
# Singleton export
# ===========================================================================

search_engine = SearchEngine()
