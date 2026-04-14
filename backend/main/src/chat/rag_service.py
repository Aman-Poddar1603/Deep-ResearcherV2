"""
rag_service.py — Retrieval, context building, and streaming generation.

Vector store: shared ChromaDB manager used by the current system.
LLM: Ollama via LangChain (async streaming).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from main.src.research.config import settings
from main.src.store.vector.DBVector import COLLECTIONS, db_vector_manager
from main.src.utils.core.task_schedular import scheduler
from main.src.utils.DRLogger import quickLog


async def _log(msg: str, level: str = "info", urgency: str = "none") -> None:
    await scheduler.schedule(
        quickLog, params={"message": msg, "level": level, "urgency": urgency}
    )


# ── config ────────────────────────────────────────────────────────────────────
OLLAMA_HOST = settings.OLLAMA_BASE_URL
CHAT_MODEL = settings.OLLAMA_MODEL
VISION_MODEL = settings.OLLAMA_VISION_MODEL or CHAT_MODEL
EMBED_MODEL = settings.OLLAMA_EMBED_MODEL
TOP_K = settings.RAG_TOP_K
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip(
    "/"
)

_raw_collection_override = [
    c.strip() for c in os.getenv("CHAT_RAG_COLLECTIONS", "").split(",") if c.strip()
]
_collection_override = [c for c in _raw_collection_override if c in COLLECTIONS]
CHAT_COLLECTIONS = tuple(_collection_override) if _collection_override else COLLECTIONS
_DIMENSION_MISMATCH_COLLECTIONS: set[str] = set()


def _chat_query_collections() -> tuple[str, ...]:
    names = {str(name).strip() for name in CHAT_COLLECTIONS if str(name).strip()}
    try:
        client = getattr(db_vector_manager, "_client", None)
        if client is not None:
            for collection in client.list_collections():
                collection_name = str(getattr(collection, "name", "")).strip()
                if collection_name.startswith("research_"):
                    names.add(collection_name)
    except Exception:
        # Fallback to static collection set when client introspection fails.
        pass
    names.difference_update(_DIMENSION_MISMATCH_COLLECTIONS)
    return tuple(sorted(names))


@dataclass
class _ScoredHit:
    doc_id: str
    document: str
    metadata: dict[str, Any]
    distance: float
    collection: str


_embeddings: OllamaEmbeddings | None = None


def _get_embeddings() -> OllamaEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_HOST)
    return _embeddings


# ── retrieval ─────────────────────────────────────────────────────────────────


def _extract_first_vector(data: Any) -> list[Any]:
    if isinstance(data, list) and data and isinstance(data[0], list):
        return data[0]
    if isinstance(data, list):
        return data
    return []


def _extract_hits(collection_name: str, result: dict[str, Any]) -> list[_ScoredHit]:
    data = result.get("data") or {}
    ids = _extract_first_vector(data.get("ids"))
    docs = _extract_first_vector(data.get("documents"))
    metas = _extract_first_vector(data.get("metadatas"))
    distances = _extract_first_vector(data.get("distances"))

    hits: list[_ScoredHit] = []
    for index, doc_id in enumerate(ids):
        document = docs[index] if index < len(docs) else ""
        if not document:
            continue
        metadata = (
            metas[index]
            if index < len(metas) and isinstance(metas[index], dict)
            else {}
        )
        distance = float(distances[index]) if index < len(distances) else 9999.0
        hits.append(
            _ScoredHit(
                doc_id=str(doc_id),
                document=str(document),
                metadata=metadata,
                distance=distance,
                collection=collection_name,
            )
        )
    return hits


async def _query_collection(
    collection_name: str, query_embedding: list[float], k: int
) -> list[_ScoredHit]:
    result = await db_vector_manager.query(
        collection_name=collection_name,
        query_embeddings=[query_embedding],
        n_results=max(1, k),
    )
    if not result.get("success"):
        failure_message = str(result.get("message") or "")
        if "expecting embedding with dimension" in failure_message.lower():
            _DIMENSION_MISMATCH_COLLECTIONS.add(collection_name)
        await _log(
            f"RAG query failed for collection '{collection_name}': {failure_message}",
            level="warning",
            urgency="none",
        )
        return []
    return _extract_hits(collection_name, result)


def _rank_hits(per_collection_hits: list[list[_ScoredHit]], k: int) -> list[_ScoredHit]:
    best_by_id: dict[str, _ScoredHit] = {}
    for collection_hits in per_collection_hits:
        for hit in collection_hits:
            current = best_by_id.get(hit.doc_id)
            if current is None or hit.distance < current.distance:
                best_by_id[hit.doc_id] = hit

    ranked = sorted(best_by_id.values(), key=lambda item: item.distance)
    return ranked[: max(1, k)]


def _format_hit(hit: _ScoredHit) -> str:
    source = (
        hit.metadata.get("source")
        or hit.metadata.get("source_url")
        or hit.metadata.get("url")
        or "unknown"
    )
    return f"[{hit.collection} | {source}]\n{hit.document}"


def _extract_source(metadata: dict[str, Any]) -> str:
    source = (
        metadata.get("source")
        or metadata.get("source_url")
        or metadata.get("url")
        or metadata.get("file")
        or metadata.get("path")
        or "unknown"
    )
    return str(source)


def _build_source_blocks(chunks: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for chunk in chunks:
        source_id = int(chunk.get("source_id") or 0)
        if source_id <= 0:
            continue
        collection = str(chunk.get("collection") or "unknown")
        source = str(chunk.get("source") or "unknown")
        content = str(chunk.get("content") or "").strip()
        lines.append(f"[Source {source_id}] {collection} | {source}")
        lines.append(content)
        lines.append("")
    return "\n".join(lines).strip()


def _is_http_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _append_query_param(url: str, key: str, value: str) -> str:
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query[key] = value
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


def _build_backend_asset_url(asset_relative_path: str) -> str:
    normalized = asset_relative_path.lstrip("/")
    return f"{BACKEND_PUBLIC_URL}/bucket/assets/{normalized}"


def _normalize_source_display(source: str) -> str:
    clean = source.strip()
    if not clean:
        return "unknown"

    if _is_http_url(clean):
        try:
            parsed = urlsplit(clean)
            if parsed.path:
                file_name = Path(parsed.path).name
                if file_name:
                    return file_name
        except Exception:
            pass
        return clean

    return Path(clean).name or clean


def _resolve_source_download_url(source: str) -> str | None:
    raw = source.strip()
    if not raw or raw.lower() == "unknown":
        return None

    if _is_http_url(raw):
        parsed = urlsplit(raw)
        if "/bucket/assets/" in parsed.path:
            return _append_query_param(raw, "download", "1")
        return raw

    if raw.startswith("/") and raw.startswith("/bucket/assets/"):
        return _append_query_param(f"{BACKEND_PUBLIC_URL}{raw}", "download", "1")

    normalized = raw.lstrip("/")
    if normalized.startswith("bucket/assets/"):
        relative_path = normalized[len("bucket/assets/") :]
        return _append_query_param(
            _build_backend_asset_url(relative_path), "download", "1"
        )

    marker = "/store/bucket/"
    if marker in raw:
        relative_path = raw.split(marker, 1)[1].lstrip("/")
        return _append_query_param(
            _build_backend_asset_url(relative_path), "download", "1"
        )

    # Handles stored bucket-relative paths such as "chat-attachments/files/doc.pdf".
    if "/" in normalized and Path(normalized).suffix:
        return _append_query_param(
            _build_backend_asset_url(normalized), "download", "1"
        )

    return None


def _build_sources_section(
    chunks: list[dict[str, Any]],
    cited_ids: list[int] | None = None,
) -> str:
    if not chunks:
        return ""

    by_id: dict[int, dict[str, Any]] = {}
    for chunk in chunks:
        source_id = int(chunk.get("source_id") or 0)
        if source_id > 0 and source_id not in by_id:
            by_id[source_id] = chunk

    selected_ids = cited_ids or []
    if not selected_ids:
        selected_ids = sorted(by_id.keys())[: min(3, len(by_id))]

    lines: list[str] = ["## Sources"]
    for source_id in selected_ids:
        chunk = by_id.get(source_id)
        if not chunk:
            continue
        source = str(chunk.get("source") or "unknown")
        collection = str(chunk.get("collection") or "unknown")
        display_source = _normalize_source_display(source)
        download_url = _resolve_source_download_url(source)
        if download_url:
            lines.append(
                f"- Source {source_id}: [{display_source}]({download_url}) ({collection})"
            )
        else:
            lines.append(f"- Source {source_id}: {display_source} ({collection})")

    return "\n".join(lines)


def _strip_existing_sources_section(response_text: str) -> str:
    marker = re.search(r"(^|\n)##\s+sources\b", response_text, flags=re.IGNORECASE)
    if not marker:
        return response_text.rstrip()
    return response_text[: marker.start()].rstrip()


def ensure_sources_section(response_text: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return response_text

    text_without_sources = _strip_existing_sources_section(response_text)

    cited = {
        int(match)
        for match in re.findall(r"\[Source\s+(\d+)\]", text_without_sources)
        if match.isdigit()
    }
    cited_ids = sorted(source_id for source_id in cited if source_id > 0)
    sources_section = _build_sources_section(chunks, cited_ids)
    if not sources_section:
        return response_text
    return f"{text_without_sources}\n\n{sources_section}\n"


def build_sources_payload(
    response_text: str,
    chunks: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """
    Build structured sources suitable for UI components:
    [{"href": "...", "title": "..."}, ...]
    """
    if not chunks:
        return []

    by_id: dict[int, dict[str, Any]] = {}
    for chunk in chunks:
        source_id = int(chunk.get("source_id") or 0)
        if source_id > 0 and source_id not in by_id:
            by_id[source_id] = chunk

    cited_ids = sorted(
        {
            int(match)
            for match in re.findall(r"\[Source\s+(\d+)\]", response_text)
            if match.isdigit()
        }
    )
    if not cited_ids:
        cited_ids = sorted(by_id.keys())[: min(3, len(by_id))]

    items: list[dict[str, str]] = []
    seen_hrefs: set[str] = set()
    for source_id in cited_ids:
        chunk = by_id.get(source_id)
        if not chunk:
            continue

        source = str(chunk.get("source") or "unknown")
        href = _resolve_source_download_url(source)
        if not href:
            continue
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        title = _normalize_source_display(source) or f"Source {source_id}"
        items.append({"href": href, "title": title})

    return items


async def retrieve_chunks(query: str, k: int = TOP_K) -> list[dict[str, Any]]:
    """Return top-k relevant text chunks across all configured collections."""
    if not query.strip():
        return []

    try:
        embedding = await asyncio.to_thread(_get_embeddings().embed_query, query)
        collection_names = _chat_query_collections()
        if not collection_names:
            return []
        per_collection_hits = await asyncio.gather(
            *[
                _query_collection(
                    collection_name=collection_name,
                    query_embedding=embedding,
                    k=k,
                )
                for collection_name in collection_names
            ]
        )
        ranked_hits = _rank_hits(per_collection_hits, k)
        return [
            {
                "source_id": index,
                "doc_id": hit.doc_id,
                "collection": hit.collection,
                "source": _extract_source(hit.metadata),
                "content": hit.document,
                "distance": hit.distance,
            }
            for index, hit in enumerate(ranked_hits, start=1)
        ]
    except Exception as exc:
        await _log(f"RAG retrieval error: {exc}", level="error", urgency="moderate")
        return []


# ── context builder ───────────────────────────────────────────────────────────


def build_context(
    history: list[dict],
    chunks: list[dict[str, Any]],
    mcp_content: str = "",
    user_name: str | None = None,
    user_location: str | None = None,
    workspace_name: str | None = None,
) -> str:
    history_text = "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in history
    )
    docs_text = _build_source_blocks(chunks) if chunks else ""
    server_now = (
        datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    clean_user_name = (user_name or "").strip()
    clean_user_location = (user_location or "").strip()
    clean_workspace_name = (workspace_name or "").strip()

    profile_lines: list[str] = []
    if clean_user_name:
        profile_lines.append(f"User Name: {clean_user_name}")
    if clean_user_location:
        profile_lines.append(f"User Location: {clean_user_location}")
    if clean_workspace_name:
        profile_lines.append(f"Workspace: {clean_workspace_name}")

    parts = [
        f"### Current Server Time\n{server_now}",
        "### User Profile\n" + "\n".join(profile_lines) if profile_lines else "",
        "### Conversation History\n" + history_text if history_text else "",
    ]
    if docs_text:
        parts.append("### Relevant Knowledge Base\n" + docs_text)
    if mcp_content.strip():
        parts.append("### Attached File Content\n" + mcp_content)

    return "\n\n".join(p for p in parts if p)


def build_langchain_messages(
    system_prompt: str,
    history: list[dict],
    context: str,
    user_query: str,
) -> list[Any]:
    msgs: list[Any] = [SystemMessage(content=system_prompt)]
    for m in history[:-1]:  # history minus the current user turn
        role = (m.get("role") or "user").lower()
        if role == "user":
            msgs.append(HumanMessage(content=m.get("content", "")))
        else:
            msgs.append(AIMessage(content=m.get("content", "")))
    # Final user message with injected context
    final = f"{context}\n\n### Current Question\n{user_query}"
    msgs.append(HumanMessage(content=final))
    return msgs


# ── streaming generation ───────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are an intelligent assistant for both general chat and retrieval-augmented answers. "
    "Prefer retrieved context when available, but if no retrieved sources exist, answer using normal assistant reasoning. "
    "For time/date questions, use the provided current server time context. "
    "When your answer uses retrieved evidence, cite inline using [Source N]. "
    "When any [Source N] is used, end the response with a markdown section exactly titled '## Sources'."
)


async def stream_rag_response(
    query: str,
    history: list[dict],
    chunks: list[dict[str, Any]],
    mcp_content: str = "",
    image_attachments: list[dict[str, str]] | None = None,
    user_name: str | None = None,
    user_location: str | None = None,
    workspace_name: str | None = None,
) -> AsyncIterator[str]:
    """
    Yield text tokens for the RAG response.
    """
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_HOST,
        temperature=0.3,
    )

    query_text = query.strip() or "Please describe the attached image(s)."
    context = build_context(
        history,
        chunks,
        mcp_content,
        user_name=user_name,
        user_location=user_location,
        workspace_name=workspace_name,
    )

    image_payloads = [
        item
        for item in (image_attachments or [])
        if item.get("data") and item.get("file_format")
    ]

    if image_payloads:
        try:
            streamed_any = False
            async for token in _stream_ollama_vision_response(
                query=query_text,
                context=context,
                image_attachments=image_payloads,
            ):
                streamed_any = True
                yield token
            if streamed_any:
                return
        except Exception as exc:
            await _log(
                f"Vision streaming failed: {exc}",
                level="warning",
                urgency="moderate",
            )
            if not chunks and not mcp_content.strip():
                yield (
                    "I received your image, but the configured model cannot analyze images. "
                    "Set OLLAMA_VISION_MODEL to a vision-capable model and try again."
                )
                return

    messages = build_langchain_messages(SYSTEM_PROMPT, history, context, query_text)
    try:
        async for chunk in llm.astream(messages):
            token = chunk.content if isinstance(chunk.content, str) else ""
            if token:
                yield token
    except Exception as exc:
        await _log(f"LLM generation error: {exc}", level="error", urgency="critical")


async def generate_thread_title(history_text: str) -> str:
    """Generate a short thread title from conversation context (non-streaming)."""
    llm = ChatOllama(
        model=CHAT_MODEL,
        base_url=OLLAMA_HOST,
        temperature=0,
    )
    prompt = (
        "Generate a short (5 words max) descriptive title for this conversation. "
        "Reply with ONLY the title, no punctuation, no quotes.\n\n"
        f"{history_text}"
    )
    result = await llm.ainvoke([HumanMessage(content=prompt)])
    content = result.content
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        text = " ".join(str(item) for item in content if item is not None)
    else:
        text = ""
    return (text or "New Chat").strip()[:80]


async def _stream_ollama_vision_response(
    query: str,
    context: str,
    image_attachments: list[dict[str, str]],
) -> AsyncIterator[str]:
    endpoint = f"{OLLAMA_HOST.rstrip('/')}/api/chat"
    user_content = f"{context}\n\n### Current Question\n{query}"
    images = [item.get("data", "") for item in image_attachments if item.get("data")]
    if not images:
        return

    payload = {
        "model": VISION_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_content,
                "images": images,
            },
        ],
        "stream": True,
        "options": {"temperature": 0.3},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", endpoint, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                event = json.loads(line)
                if event.get("error"):
                    raise RuntimeError(str(event.get("error")))
                message = event.get("message") or {}
                token = message.get("content") or ""
                if token:
                    yield token
