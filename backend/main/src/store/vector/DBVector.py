"""
DBVector.py — Deep Researcher v2
=================================
Collection-agnostic ChromaDB CRUD manager with SQLite3 WAL metadata store.

Design:
  - DBVectorManager  : thin ChromaDB wrapper; all methods accept collection_name.
  - MetadataStore    : SQLite3 (WAL mode) for relational status tracking.
  - Singleton exports: `db_vector_manager`, `metadata_store`

All heavy lifting (chunking, embedding, ingestion) lives in IngestionService.py.
All search orchestration lives in SearchEngine.py.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import chromadb
from main.src.utils.DRLogger import LogType, dr_logger
from main.src.utils.versionManagement import getAppVersion

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent  # .../store/
SRC_DIR = BASE_DIR.parent  # .../src/

for _p in [str(SRC_DIR), str(SRC_DIR.parent)]:
    if _p not in sys.path:
        sys.path.append(_p)

logging.basicConfig(level=logging.INFO)
_std_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported collections
# ---------------------------------------------------------------------------
COLLECTIONS = ("websites", "pdfs", "images", "custom", "research")

# ---------------------------------------------------------------------------
# Logging helpers (mirrors original DRLogger pattern)
# ---------------------------------------------------------------------------


def _log(level: LogType, message: str, urgency: str = "none") -> None:
    """Dual-write to stdlib logger and DRLogger."""
    getattr(_std_logger, level if level in ("info", "warning", "error") else "info")(
        message
    )
    try:
        dr_logger.log(
            log_type=level,
            message=message,
            origin="system",
            module="DB",
            urgency=urgency,
            app_version=getAppVersion(),
        )
    except Exception as exc:
        _std_logger.error(f"DRLogger internal failure: {exc}")


# ===========================================================================
# MetadataStore  —  SQLite3 (WAL) relational sidecar
# ===========================================================================


class MetadataStore:
    """
    SQLite3 metadata sidecar for ChromaDB vector entries.

    Schema
    ------
    vector_entries(
        id          TEXT PRIMARY KEY,
        collection  TEXT NOT NULL,
        source_uri  TEXT,
        content_hash TEXT,
        status      TEXT DEFAULT 'pending',  -- pending | indexed | error
        created_at  INTEGER,                 -- Unix epoch
        updated_at  INTEGER
    )

    WAL mode is enabled on every connection for concurrent-write safety.
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = str(db_path)
        self._local = None  # We create per-thread connections via _conn()
        self._init_db()
        _log("info", f"MetadataStore initialised at '{self.db_path}' (WAL mode)")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection with WAL mode active."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vector_entries (
                    id            TEXT PRIMARY KEY,
                    collection    TEXT NOT NULL,
                    source_uri    TEXT,
                    content_hash  TEXT,
                    status        TEXT NOT NULL DEFAULT 'pending',
                    created_at    INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    updated_at    INTEGER NOT NULL DEFAULT (strftime('%s','now'))
                )
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ve_collection
                ON vector_entries(collection)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ve_status
                ON vector_entries(collection, status)
            """
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Async public API (offload blocking sqlite calls to thread)
    # ------------------------------------------------------------------

    async def upsert(
        self,
        id: str,
        collection: str,
        source_uri: str = "",
        content_hash: str = "",
        status: str = "indexed",
    ) -> None:
        def _run():
            with self._conn() as conn:
                conn.execute(
                    """
                    INSERT INTO vector_entries
                        (id, collection, source_uri, content_hash, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, strftime('%s','now'))
                    ON CONFLICT(id) DO UPDATE SET
                        status       = excluded.status,
                        content_hash = excluded.content_hash,
                        updated_at   = excluded.updated_at
                """,
                    (id, collection, source_uri, content_hash, status),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def mark_status(self, id: str, status: str) -> None:
        def _run():
            with self._conn() as conn:
                conn.execute(
                    """
                    UPDATE vector_entries
                    SET status = ?, updated_at = strftime('%s','now')
                    WHERE id = ?
                """,
                    (status, id),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def fetch_by_collection(
        self,
        collection: str,
        status: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        def _run():
            with self._conn() as conn:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM vector_entries WHERE collection=? AND status=? LIMIT ?",
                        (collection, status, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM vector_entries WHERE collection=? LIMIT ?",
                        (collection, limit),
                    ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def fetch_one(self, id: str) -> Optional[Dict[str, Any]]:
        def _run():
            with self._conn() as conn:
                row = conn.execute(
                    "SELECT * FROM vector_entries WHERE id=?", (id,)
                ).fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def delete(self, ids: List[str]) -> int:
        def _run():
            with self._conn() as conn:
                placeholders = ",".join("?" * len(ids))
                cur = conn.execute(
                    f"DELETE FROM vector_entries WHERE id IN ({placeholders})", ids
                )
                conn.commit()
                return cur.rowcount

        return await asyncio.to_thread(_run)

    async def collection_stats(self) -> Dict[str, Any]:
        def _run():
            with self._conn() as conn:
                rows = conn.execute(
                    """
                    SELECT collection, status, COUNT(*) as cnt
                    FROM vector_entries
                    GROUP BY collection, status
                """
                ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_run)


# ===========================================================================
# DBVectorManager  —  collection-agnostic ChromaDB CRUD
# ===========================================================================


class DBVectorManager:
    """
    Collection-agnostic ChromaDB CRUD wrapper for Deep Researcher v2.

    Key changes from v1
    --------------------
    - The singleton no longer hard-codes a single collection.
    - All CRUD methods accept ``collection_name`` as a first-class parameter.
    - Collections are lazily created on first access and cached in ``_cols``.
    - Pre-computed ``embeddings`` are **always** supplied by callers; this class
      never calls Ollama / SigLIP directly (that is IngestionService's job).

    Collections
    -----------
    "websites" | "pdfs" | "images" | "custom"

    Return contract
    ---------------
    Every public method returns::

        {"success": bool, "message": str, "data": Any | None}
    """

    def __init__(self, persist_directory: Union[str, Path]) -> None:
        self.persist_directory = str(persist_directory)
        self._client = chromadb.PersistentClient(path=self.persist_directory)
        self._cols: Dict[str, Any] = {}  # collection cache
        _log("info", f"DBVectorManager ready at '{self.persist_directory}'")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _col(self, collection_name: str):
        """Return (cached) ChromaDB collection handle, no embedding function
        because callers always supply pre-computed vectors."""
        if collection_name not in self._cols:
            if collection_name not in COLLECTIONS:
                raise ValueError(
                    f"Unknown collection '{collection_name}'. Valid: {COLLECTIONS}"
                )
            self._cols[collection_name] = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
                # No embedding_function — we always pass pre-computed embeddings
            )
            _log("info", f"Collection '{collection_name}' opened/created.")
        return self._cols[collection_name]

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def add(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Insert documents with pre-computed embeddings. Skips duplicate IDs."""
        _log("info", f"add() → '{collection_name}' × {len(ids)} docs")
        if not ids:
            return {"success": False, "message": "ids must be non-empty.", "data": None}

        try:
            col = self._col(collection_name)

            # Filter out IDs that already exist
            existing = await asyncio.to_thread(col.get, ids=ids)
            existing_ids = set(existing.get("ids", []))
            if existing_ids:
                _log(
                    "warning",
                    f"Skipping {len(existing_ids)} duplicate IDs in '{collection_name}'.",
                )
                mask = [i for i, id_ in enumerate(ids) if id_ not in existing_ids]
                ids = [ids[i] for i in mask]
                embeddings = [embeddings[i] for i in mask]
                documents = [documents[i] for i in mask] if documents else documents
                metadatas = [metadatas[i] for i in mask] if metadatas else metadatas

            if not ids:
                return {
                    "success": True,
                    "message": "All IDs already exist; nothing added.",
                    "data": {"count": 0},
                }

            kwargs: Dict[str, Any] = {"ids": ids, "embeddings": embeddings}
            if documents is not None:
                kwargs["documents"] = documents
            if metadatas is not None:
                kwargs["metadatas"] = metadatas

            await asyncio.to_thread(col.add, **kwargs)
            _log("success", f"Added {len(ids)} docs to '{collection_name}'.")
            return {
                "success": True,
                "message": f"{len(ids)} document(s) added.",
                "data": {"count": len(ids)},
            }

        except Exception as exc:
            _log("error", f"add() failed on '{collection_name}': {exc}", "moderate")
            return {"success": False, "message": str(exc), "data": None}

    async def upsert(
        self,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Upsert documents — add if missing, update if present."""
        _log("info", f"upsert() → '{collection_name}' × {len(ids)} docs")
        if not ids:
            return {"success": False, "message": "ids must be non-empty.", "data": None}

        try:
            col = self._col(collection_name)
            kwargs: Dict[str, Any] = {"ids": ids, "embeddings": embeddings}
            if documents is not None:
                kwargs["documents"] = documents
            if metadatas is not None:
                kwargs["metadatas"] = metadatas

            await asyncio.to_thread(col.upsert, **kwargs)
            _log("success", f"Upserted {len(ids)} docs in '{collection_name}'.")
            return {
                "success": True,
                "message": f"{len(ids)} document(s) upserted.",
                "data": {"count": len(ids)},
            }

        except Exception as exc:
            _log("error", f"upsert() failed on '{collection_name}': {exc}", "moderate")
            return {"success": False, "message": str(exc), "data": None}

    async def query(
        self,
        collection_name: str,
        query_embeddings: List[List[float]],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """ANN similarity search. Returns top-k results per query embedding."""
        _log("info", f"query() → '{collection_name}' k={n_results}")
        include = include or ["documents", "metadatas", "distances"]

        try:
            col = self._col(collection_name)

            # Guard: ChromaDB errors if n_results > collection size
            count = await asyncio.to_thread(col.count)
            k = min(n_results, max(count, 1))

            kwargs: Dict[str, Any] = {
                "query_embeddings": query_embeddings,
                "n_results": k,
                "include": include,
            }
            if where:
                kwargs["where"] = where

            result = await asyncio.to_thread(col.query, **kwargs)
            _log("success", f"query() returned results from '{collection_name}'.")
            return {"success": True, "message": "Query complete.", "data": result}

        except Exception as exc:
            _log("error", f"query() failed on '{collection_name}': {exc}", "moderate")
            return {"success": False, "message": str(exc), "data": None}

    async def fetch_all(
        self,
        collection_name: str,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieve documents with optional metadata filter (SELECT *)."""
        _log("info", f"fetch_all() → '{collection_name}'")
        try:
            col = self._col(collection_name)
            kwargs: Dict[str, Any] = {"include": ["documents", "metadatas"]}
            if where is not None:
                kwargs["where"] = where
            if limit is not None:
                kwargs["limit"] = limit
            if offset is not None:
                kwargs["offset"] = offset

            result = await asyncio.to_thread(col.get, **kwargs)
            ids = result.get("ids", [])
            _log("success", f"Fetched {len(ids)} docs from '{collection_name}'.")
            return {
                "success": True,
                "message": f"Fetched {len(ids)} document(s).",
                "data": {
                    "ids": ids,
                    "documents": result.get("documents"),
                    "metadatas": result.get("metadatas"),
                },
            }
        except Exception as exc:
            _log(
                "error", f"fetch_all() failed on '{collection_name}': {exc}", "moderate"
            )
            return {"success": False, "message": str(exc), "data": None}

    async def fetch_one(self, collection_name: str, id: str) -> Dict[str, Any]:
        """Retrieve a single document by ID."""
        _log("info", f"fetch_one('{id}') → '{collection_name}'")
        if not id:
            return {"success": False, "message": "id must be non-empty.", "data": None}
        try:
            col = self._col(collection_name)
            result = await asyncio.to_thread(
                col.get, ids=[id], include=["documents", "metadatas"]
            )
            ids_ = result.get("ids", [])
            if not ids_:
                return {
                    "success": True,
                    "message": f"Document '{id}' not found.",
                    "data": None,
                }
            return {
                "success": True,
                "message": f"Document '{id}' fetched.",
                "data": {
                    "id": ids_[0],
                    "document": (result.get("documents") or [None])[0],
                    "metadata": (result.get("metadatas") or [None])[0],
                },
            }
        except Exception as exc:
            _log("error", f"fetch_one() failed: {exc}", "moderate")
            return {"success": False, "message": str(exc), "data": None}

    async def update(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """Update existing documents (partial field overwrite)."""
        if not ids:
            return {"success": False, "message": "ids must be non-empty.", "data": None}
        if documents is None and metadatas is None and embeddings is None:
            return {
                "success": False,
                "message": "Provide at least one of: documents, metadatas, embeddings.",
                "data": None,
            }

        try:
            col = self._col(collection_name)
            kwargs: Dict[str, Any] = {"ids": ids}
            if documents is not None:
                kwargs["documents"] = documents
            if metadatas is not None:
                kwargs["metadatas"] = metadatas
            if embeddings is not None:
                kwargs["embeddings"] = embeddings

            await asyncio.to_thread(col.update, **kwargs)
            _log("success", f"Updated {len(ids)} docs in '{collection_name}'.")
            return {
                "success": True,
                "message": f"{len(ids)} document(s) updated.",
                "data": {"count": len(ids)},
            }

        except Exception as exc:
            _log("error", f"update() failed on '{collection_name}': {exc}", "moderate")
            return {"success": False, "message": str(exc), "data": None}

    async def delete(self, collection_name: str, ids: List[str]) -> Dict[str, Any]:
        """Permanently remove documents by ID."""
        if not ids:
            return {"success": False, "message": "ids must be non-empty.", "data": None}
        try:
            col = self._col(collection_name)
            await asyncio.to_thread(col.delete, ids=ids)
            _log("success", f"Deleted {len(ids)} docs from '{collection_name}'.")
            return {
                "success": True,
                "message": f"{len(ids)} document(s) deleted.",
                "data": {"count": len(ids)},
            }
        except Exception as exc:
            _log("error", f"delete() failed on '{collection_name}': {exc}", "moderate")
            return {"success": False, "message": str(exc), "data": None}

    async def collection_health(self, collection_name: str) -> Dict[str, Any]:
        """Returns document count for the named collection."""
        try:
            col = self._col(collection_name)
            count = await asyncio.to_thread(col.count)
            return {
                "success": True,
                "message": f"Collection '{collection_name}' is accessible.",
                "data": {"collection_name": collection_name, "count": count},
            }
        except Exception as exc:
            _log(
                "error",
                f"health check failed on '{collection_name}': {exc}",
                "critical",
            )
            return {"success": False, "message": str(exc), "data": None}

    async def all_collection_health(self) -> Dict[str, Any]:
        """Health-check all managed collections concurrently."""
        results = await asyncio.gather(
            *[self.collection_health(c) for c in COLLECTIONS],
            return_exceptions=False,
        )
        return dict(zip(COLLECTIONS, results))


# ===========================================================================
# Domain metadata stores  —  SQLiteManager-backed ORM tables
# ===========================================================================
# These stores write into the same SQLite files managed by DBManager.py
# (buckets.db, researches.db, scrapes.db).  They are purely relational —
# ChromaDB's HNSW search never touches them.  Use them for:
#   • listing / filtering by domain entity (bucket, research, scrape)
#   • status tracking & audit trails at the domain level
#   • foreign-key joins that ChromaDB cannot express
#
# Import pattern (mirrors DBManager exports):
#
#   from main.src.store.DBManager import (
#       buckets_db_manager,
#       researches_db_manager,
#       scrapes_db_manager,
#   )
#   from main.src.store.DBVector import (
#       bucket_meta_store,
#       research_meta_store,
#       scrape_meta_store,
#   )
# ===========================================================================


class BucketMetaStore:
    """
    Relational metadata store for Bucket entities.

    Backed by ``buckets.db.sqlite3`` via ``buckets_db_manager``.

    Schema
    ------
    bucket_meta(
        bucket_id     TEXT PRIMARY KEY,
        name          TEXT NOT NULL,
        description   TEXT,
        status        TEXT DEFAULT 'active',   -- active | archived | deleted
        vector_collection TEXT,                -- ChromaDB collection name, if any
        created_at    INTEGER,
        updated_at    INTEGER
    )

    Note
    ----
    ChromaDB's ANN search is unaffected by this table.  This store is purely
    for relational queries (list buckets, filter by status, etc.).
    """

    def __init__(self, db_manager) -> None:
        """
        Parameters
        ----------
        db_manager : SQLiteManager
            The ``buckets_db_manager`` singleton from DBManager.py.
        """
        self._mgr = db_manager
        self._init_table()
        _log("info", "BucketMetaStore initialised (buckets.db)")

    def _init_table(self) -> None:
        with self._mgr._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bucket_meta (
                    bucket_id         TEXT PRIMARY KEY,
                    name              TEXT NOT NULL,
                    description       TEXT,
                    status            TEXT NOT NULL DEFAULT 'active',
                    vector_collection TEXT,
                    created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    updated_at        INTEGER NOT NULL DEFAULT (strftime('%s','now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bm_status ON bucket_meta(status)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def upsert(
        self,
        bucket_id: str,
        name: str,
        description: str = "",
        status: str = "active",
        vector_collection: Optional[str] = None,
    ) -> None:
        """Insert or update a bucket metadata record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO bucket_meta
                        (bucket_id, name, description, status, vector_collection, updated_at)
                    VALUES (?, ?, ?, ?, ?, strftime('%s','now'))
                    ON CONFLICT(bucket_id) DO UPDATE SET
                        name              = excluded.name,
                        description       = excluded.description,
                        status            = excluded.status,
                        vector_collection = excluded.vector_collection,
                        updated_at        = excluded.updated_at
                    """,
                    (bucket_id, name, description, status, vector_collection),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def mark_status(self, bucket_id: str, status: str) -> None:
        """Update only the status field of a bucket record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE bucket_meta
                    SET status = ?, updated_at = strftime('%s','now')
                    WHERE bucket_id = ?
                    """,
                    (status, bucket_id),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def fetch_one(self, bucket_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single bucket record by ID."""

        def _run():
            with self._mgr._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM bucket_meta WHERE bucket_id = ?", (bucket_id,)
                ).fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def fetch_all(
        self,
        status: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List all buckets, optionally filtered by status."""

        def _run():
            with self._mgr._get_connection() as conn:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM bucket_meta WHERE status = ? LIMIT ?",
                        (status, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM bucket_meta LIMIT ?", (limit,)
                    ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def delete(self, bucket_id: str) -> None:
        """Hard-delete a bucket metadata record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    "DELETE FROM bucket_meta WHERE bucket_id = ?", (bucket_id,)
                )
                conn.commit()

        await asyncio.to_thread(_run)


class ResearchMetaStore:
    """
    Relational metadata store for Research entities.

    Backed by ``researches.db.sqlite3`` via ``researches_db_manager``.

    Schema
    ------
    research_meta(
        research_id   TEXT PRIMARY KEY,
        bucket_id     TEXT NOT NULL,            -- logical FK → bucket_meta.bucket_id
        title         TEXT,
        query         TEXT,
        status        TEXT DEFAULT 'pending',   -- pending | running | done | error
        vector_collection TEXT DEFAULT 'research',
        created_at    INTEGER,
        updated_at    INTEGER
    )

    Note
    ----
    ``vector_collection`` defaults to "research" — the ChromaDB collection
    added in this module.  The ANN search itself runs inside ChromaDB and is
    decoupled from this relational store.
    """

    def __init__(self, db_manager) -> None:
        """
        Parameters
        ----------
        db_manager : SQLiteManager
            The ``researches_db_manager`` singleton from DBManager.py.
        """
        self._mgr = db_manager
        self._init_table()
        _log("info", "ResearchMetaStore initialised (researches.db)")

    def _init_table(self) -> None:
        with self._mgr._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS research_meta (
                    research_id       TEXT PRIMARY KEY,
                    bucket_id         TEXT NOT NULL,
                    title             TEXT,
                    query             TEXT,
                    status            TEXT NOT NULL DEFAULT 'pending',
                    vector_collection TEXT NOT NULL DEFAULT 'research',
                    created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    updated_at        INTEGER NOT NULL DEFAULT (strftime('%s','now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rm_bucket ON research_meta(bucket_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rm_status ON research_meta(bucket_id, status)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def upsert(
        self,
        research_id: str,
        bucket_id: str,
        title: str = "",
        query: str = "",
        status: str = "pending",
        vector_collection: str = "research",
    ) -> None:
        """Insert or update a research metadata record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO research_meta
                        (research_id, bucket_id, title, query, status, vector_collection, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, strftime('%s','now'))
                    ON CONFLICT(research_id) DO UPDATE SET
                        bucket_id         = excluded.bucket_id,
                        title             = excluded.title,
                        query             = excluded.query,
                        status            = excluded.status,
                        vector_collection = excluded.vector_collection,
                        updated_at        = excluded.updated_at
                    """,
                    (research_id, bucket_id, title, query, status, vector_collection),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def mark_status(self, research_id: str, status: str) -> None:
        """Update only the status field of a research record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE research_meta
                    SET status = ?, updated_at = strftime('%s','now')
                    WHERE research_id = ?
                    """,
                    (status, research_id),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def fetch_by_bucket(
        self,
        bucket_id: str,
        status: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List all researches for a given bucket, optionally filtered by status."""

        def _run():
            with self._mgr._get_connection() as conn:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM research_meta WHERE bucket_id = ? AND status = ? LIMIT ?",
                        (bucket_id, status, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM research_meta WHERE bucket_id = ? LIMIT ?",
                        (bucket_id, limit),
                    ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def fetch_one(self, research_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single research record by ID."""

        def _run():
            with self._mgr._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM research_meta WHERE research_id = ?", (research_id,)
                ).fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def delete(self, research_id: str) -> None:
        """Hard-delete a research metadata record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    "DELETE FROM research_meta WHERE research_id = ?", (research_id,)
                )
                conn.commit()

        await asyncio.to_thread(_run)


class ScrapeMetaStore:
    """
    Relational metadata store for web-crawl / scrape page entities.

    Backed by ``scrapes.db.sqlite3`` via ``scrapes_db_manager``.

    Schema
    ------
    scrape_meta(
        scrape_id     TEXT PRIMARY KEY,
        research_id   TEXT NOT NULL,            -- logical FK → research_meta.research_id
        bucket_id     TEXT NOT NULL,            -- logical FK → bucket_meta.bucket_id
        url           TEXT NOT NULL,
        content_hash  TEXT,
        status        TEXT DEFAULT 'pending',   -- pending | scraped | indexed | error
        vector_collection TEXT DEFAULT 'websites',
        scraped_at    INTEGER,
        created_at    INTEGER,
        updated_at    INTEGER
    )

    Note
    ----
    ``vector_collection`` records which ChromaDB collection holds this page's
    chunks ("websites" by default).  The ANN search runs inside ChromaDB and
    is fully decoupled from this store.
    """

    def __init__(self, db_manager) -> None:
        """
        Parameters
        ----------
        db_manager : SQLiteManager
            The ``scrapes_db_manager`` singleton from DBManager.py.
        """
        self._mgr = db_manager
        self._init_table()
        _log("info", "ScrapeMetaStore initialised (scrapes.db)")

    def _init_table(self) -> None:
        with self._mgr._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scrape_meta (
                    scrape_id         TEXT PRIMARY KEY,
                    research_id       TEXT NOT NULL,
                    bucket_id         TEXT NOT NULL,
                    url               TEXT NOT NULL,
                    content_hash      TEXT,
                    status            TEXT NOT NULL DEFAULT 'pending',
                    vector_collection TEXT NOT NULL DEFAULT 'websites',
                    scraped_at        INTEGER,
                    created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now')),
                    updated_at        INTEGER NOT NULL DEFAULT (strftime('%s','now'))
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sm_research ON scrape_meta(research_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sm_bucket ON scrape_meta(bucket_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sm_status ON scrape_meta(research_id, status)"
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def upsert(
        self,
        scrape_id: str,
        research_id: str,
        bucket_id: str,
        url: str,
        content_hash: str = "",
        status: str = "pending",
        vector_collection: str = "websites",
        scraped_at: Optional[int] = None,
    ) -> None:
        """Insert or update a scrape page metadata record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO scrape_meta
                        (scrape_id, research_id, bucket_id, url, content_hash,
                         status, vector_collection, scraped_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s','now'))
                    ON CONFLICT(scrape_id) DO UPDATE SET
                        status            = excluded.status,
                        content_hash      = excluded.content_hash,
                        vector_collection = excluded.vector_collection,
                        scraped_at        = excluded.scraped_at,
                        updated_at        = excluded.updated_at
                    """,
                    (
                        scrape_id,
                        research_id,
                        bucket_id,
                        url,
                        content_hash,
                        status,
                        vector_collection,
                        scraped_at,
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def mark_status(self, scrape_id: str, status: str) -> None:
        """Update only the status field of a scrape record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE scrape_meta
                    SET status = ?, updated_at = strftime('%s','now')
                    WHERE scrape_id = ?
                    """,
                    (status, scrape_id),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def fetch_by_research(
        self,
        research_id: str,
        status: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """List all scrape pages for a given research, optionally filtered by status."""

        def _run():
            with self._mgr._get_connection() as conn:
                if status:
                    rows = conn.execute(
                        "SELECT * FROM scrape_meta WHERE research_id = ? AND status = ? LIMIT ?",
                        (research_id, status, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM scrape_meta WHERE research_id = ? LIMIT ?",
                        (research_id, limit),
                    ).fetchall()
                return [dict(r) for r in rows]

        return await asyncio.to_thread(_run)

    async def fetch_one(self, scrape_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single scrape record by ID."""

        def _run():
            with self._mgr._get_connection() as conn:
                row = conn.execute(
                    "SELECT * FROM scrape_meta WHERE scrape_id = ?", (scrape_id,)
                ).fetchone()
                return dict(row) if row else None

        return await asyncio.to_thread(_run)

    async def delete(self, scrape_id: str) -> None:
        """Hard-delete a scrape metadata record."""

        def _run():
            with self._mgr._get_connection() as conn:
                conn.execute(
                    "DELETE FROM scrape_meta WHERE scrape_id = ?", (scrape_id,)
                )
                conn.commit()

        await asyncio.to_thread(_run)


# ===========================================================================
# Initialisation helpers
# ===========================================================================


def _ensure_dirs() -> None:
    for subdir in ("chroma_store", "sqlite"):
        d = BASE_DIR / "database" / subdir
        try:
            d.mkdir(parents=True, exist_ok=True)
            _std_logger.info(f"Directory ensured: {d}")
        except Exception as exc:
            _std_logger.error(f"Failed to create {d}: {exc}")


# ---------------------------------------------------------------------------
# Module-level initialisation & singleton exports
# ---------------------------------------------------------------------------
if not any(x in " ".join(sys.argv) for x in ("unittest", "pytest")):
    _ensure_dirs()

_CHROMA_PATH = BASE_DIR / "database" / "chroma_store"
_SQLITE_PATH = BASE_DIR / "database" / "sqlite" / "metadata.db"

# Singleton exports — import these everywhere
db_vector_manager: DBVectorManager = DBVectorManager(persist_directory=_CHROMA_PATH)
metadata_store: MetadataStore = MetadataStore(db_path=_SQLITE_PATH)

# ---------------------------------------------------------------------------
# Domain-specific metadata store singletons
# ---------------------------------------------------------------------------
# These write into the DBManager-owned SQLite files.  Import pattern:
#
#   from main.src.store.DBVector import (
#       bucket_meta_store,
#       research_meta_store,
#       scrape_meta_store,
#   )
# ---------------------------------------------------------------------------
from main.src.store.DBManager import (  # noqa: E402 — intentional late import
    buckets_db_manager,
    researches_db_manager,
    scrapes_db_manager,
)

bucket_meta_store: BucketMetaStore = BucketMetaStore(db_manager=buckets_db_manager)
research_meta_store: ResearchMetaStore = ResearchMetaStore(
    db_manager=researches_db_manager
)
scrape_meta_store: ScrapeMetaStore = ScrapeMetaStore(db_manager=scrapes_db_manager)
