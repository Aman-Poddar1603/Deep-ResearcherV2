"""
IngestionService.py — Deep Researcher v2
=========================================
Agentic ingestion pipeline:

  ┌─────────────────────────┐
  │   IngestionRouter       │  ← public entry point
  │   submit(task)          │
  └──────────┬──────────────┘
             │  asyncio.PriorityQueue
  ┌──────────▼──────────────────────────────────────────────────┐
  │                   Worker Pool (3 workers)                   │
  │  WebWorker   PDFWorker   ImageWorker  (all async)           │
  └──────────┬─────────────────────────────────────────────────┘
             │
  ┌──────────▼──────────────────────────────────────────────────┐
  │  Embed (Ollama batched HTTP  /  SigLIP in ThreadPoolExecutor│
  │  Write  ChromaDB + SQLite3 (WAL) in parallel               │
  └─────────────────────────────────────────────────────────────┘

Task priority levels:
  0 = HIGH  (user-initiated, interactive)
  1 = NORMAL
  2 = LOW   (background pre-fetch)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

from main.src.utils.DRLogger import dr_logger, LogType
from main.src.utils.versionManagement import getAppVersion
from main.src.utils.task_scheduler import scheduler

# Lazy import so the module loads even without GPU dependencies at import time
_siglip_embedder = None


def _get_siglip():
    global _siglip_embedder
    if _siglip_embedder is None:
        from main.src.utils.core.ai.imageEmbedder import SigLIPEmbedder

        _siglip_embedder = SigLIPEmbedder()
    return _siglip_embedder


# Local singletons (imported from DBVector)
from main.src.store.DBVector import db_vector_manager, metadata_store

_std_logger = logging.getLogger(__name__)

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_MODEL = "embeddinggemma:latest"
EMBED_BATCH_SIZE = 50  # chunks per Ollama HTTP request
MAX_WORKERS = 4  # ThreadPoolExecutor threads for ONNX/SigLIP
WORKER_COUNT = 3  # asyncio coroutine workers per queue


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
            module="INGESTION",
            urgency=urgency,
            app_version=getAppVersion(),
        )
    except Exception as exc:
        _std_logger.error(f"DRLogger failure: {exc}")


# ===========================================================================
# Data structures
# ===========================================================================


class Priority(IntEnum):
    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass(order=True)
class IngestionTask:
    """
    Queued ingestion unit.

    Fields
    ------
    priority    : 0=HIGH, 1=NORMAL, 2=LOW
    collection  : "websites" | "pdfs" | "images" | "custom"
    content     : raw text / file path (str) / image bytes (bytes)
    source_uri  : canonical URL or file path for metadata
    metadata    : extra key-value pairs stored alongside the vector
    task_id     : auto-generated UUID
    """

    priority: int
    collection: str = field(compare=False)
    content: Any = field(compare=False)
    source_uri: str = field(compare=False, default="")
    metadata: Dict[str, Any] = field(compare=False, default_factory=dict)
    task_id: str = field(compare=False, default_factory=lambda: str(uuid.uuid4()))


# ===========================================================================
# Chunking helpers
# ===========================================================================


class MarkdownChunker:
    """
    Splits Markdown / HTML-cleaned web content on H1/H2/H3 headers.
    Falls back to sentence-window chunking when no headers are found.
    """

    _HEADER_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    _MAX_CHARS = 1500

    @classmethod
    def chunk(cls, text: str, source_uri: str = "") -> List[Dict[str, Any]]:
        text = cls._clean(text)
        sections = cls._split_on_headers(text)
        chunks: List[Dict[str, Any]] = []

        for section_title, section_body in sections:
            for part in cls._window_split(section_body):
                chunks.append(
                    {
                        "text": part.strip(),
                        "section": section_title,
                        "source": source_uri,
                    }
                )

        if not chunks:
            # Fallback: plain window split
            for part in cls._window_split(text):
                chunks.append(
                    {"text": part.strip(), "section": "", "source": source_uri}
                )

        return [c for c in chunks if c["text"]]

    @staticmethod
    def _clean(text: str) -> str:
        # Remove HTML tags if any leaked through
        text = re.sub(r"<[^>]+>", " ", text)
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def _split_on_headers(cls, text: str) -> List[tuple]:
        matches = list(cls._HEADER_RE.finditer(text))
        if not matches:
            return [("", text)]

        sections = []
        for i, m in enumerate(matches):
            title = m.group(2)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections.append((title, text[start:end]))
        return sections

    @classmethod
    def _window_split(cls, text: str) -> List[str]:
        if len(text) <= cls._MAX_CHARS:
            return [text]
        # Split on paragraph boundaries first
        paras = text.split("\n\n")
        chunks, buf = [], ""
        for para in paras:
            if len(buf) + len(para) > cls._MAX_CHARS:
                if buf:
                    chunks.append(buf)
                buf = para
            else:
                buf = (buf + "\n\n" + para).strip()
        if buf:
            chunks.append(buf)
        return chunks or [text[: cls._MAX_CHARS]]


class PageChunker:
    """
    Page-based PDF chunker using PyMuPDF (fitz).
    Each page becomes one or more chunks of ≤ MAX_CHARS characters.
    """

    _MAX_CHARS = 2000

    @classmethod
    def chunk(cls, pdf_path: str) -> List[Dict[str, Any]]:
        try:
            import fitz  # type: ignore
        except ImportError:
            _log(
                "error", "PyMuPDF (fitz) not installed. pip install pymupdf", "critical"
            )
            return []

        chunks: List[Dict[str, Any]] = []
        try:
            doc = fitz.open(pdf_path)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                for part in MarkdownChunker._window_split(text):
                    if part.strip():
                        chunks.append(
                            {
                                "text": part.strip(),
                                "page": page_num,
                                "source": pdf_path,
                                "total_pages": len(doc),
                            }
                        )
            doc.close()
        except Exception as exc:
            _log("error", f"PDF chunking failed for '{pdf_path}': {exc}", "moderate")
        return chunks


# ===========================================================================
# Embedding helpers
# ===========================================================================


async def _embed_texts_ollama(texts: List[str]) -> List[List[float]]:
    """
    Batch-embed text chunks via Ollama HTTP API.
    Sends EMBED_BATCH_SIZE chunks per request for maximum throughput.
    Returns embeddings in the same order as input texts.
    """
    all_embeddings: List[List[float]] = []

    async with aiohttp.ClientSession() as session:
        for batch_start in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[batch_start : batch_start + EMBED_BATCH_SIZE]
            batch_embeddings: List[List[float]] = []

            for text in batch:
                payload = {"model": OLLAMA_MODEL, "prompt": text}
                try:
                    async with session.post(OLLAMA_EMBED_URL, json=payload) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        batch_embeddings.append(data["embedding"])
                except Exception as exc:
                    _log("error", f"Ollama embedding failed: {exc}", "moderate")
                    batch_embeddings.append([])  # placeholder to keep alignment

            all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def _embed_image_siglip(
    image_input: Any,
    executor: ThreadPoolExecutor,
) -> List[float]:
    """
    Run SigLIPEmbedder.embed() in a ThreadPoolExecutor to avoid blocking
    the event loop during ONNX inference.

    ``image_input`` may be a file path (str/Path) or raw bytes.
    Returns a unit-normalised List[float].
    """
    loop = asyncio.get_event_loop()

    def _run() -> List[float]:
        embedder = _get_siglip()
        return embedder.embed(image_input)  # returns List[float]

    return await loop.run_in_executor(executor, _run)


# ===========================================================================
# Content hash
# ===========================================================================


def _content_hash(data: Any) -> str:
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()[:16]
    return hashlib.sha256(str(data).encode()).hexdigest()[:16]


# ===========================================================================
# Worker coroutines
# ===========================================================================


async def _process_website(
    task: IngestionTask,
    executor: ThreadPoolExecutor,
) -> None:
    """Chunk → embed (Ollama) → write ChromaDB + SQLite."""
    _log(
        "info",
        f"[WebWorker] Processing website task {task.task_id} from '{task.source_uri}'",
    )

    chunks = MarkdownChunker.chunk(task.content, source_uri=task.source_uri)
    if not chunks:
        _log("warning", f"[WebWorker] No chunks extracted from '{task.source_uri}'.")
        return

    texts = [c["text"] for c in chunks]
    embeddings = await _embed_texts_ollama(texts)

    ids, valid_embeddings, docs, metas = [], [], [], []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        if not emb:
            continue
        chunk_id = f"web-{_content_hash(chunk['text'])}-{i}"
        ids.append(chunk_id)
        valid_embeddings.append(emb)
        docs.append(chunk["text"])
        metas.append(
            {
                "source": chunk.get("source", task.source_uri),
                "section": chunk.get("section", ""),
                "type": "website",
                **task.metadata,
            }
        )

    if not ids:
        _log("warning", f"[WebWorker] All embeddings empty for '{task.source_uri}'.")
        return

    # Parallel write: ChromaDB + SQLite
    await asyncio.gather(
        db_vector_manager.upsert("websites", ids, valid_embeddings, docs, metas),
        *[
            metadata_store.upsert(
                id=id_,
                collection="websites",
                source_uri=task.source_uri,
                content_hash=_content_hash(doc),
                status="indexed",
            )
            for id_, doc in zip(ids, docs)
        ],
    )
    _log("success", f"[WebWorker] Indexed {len(ids)} chunks from '{task.source_uri}'.")


async def _process_pdf(
    task: IngestionTask,
    executor: ThreadPoolExecutor,
) -> None:
    """Chunk pages → embed (Ollama) → write ChromaDB + SQLite."""
    _log("info", f"[PDFWorker] Processing PDF task {task.task_id}: '{task.source_uri}'")

    pdf_path = task.content  # should be a file path string
    chunks = await asyncio.to_thread(PageChunker.chunk, pdf_path)

    if not chunks:
        _log("warning", f"[PDFWorker] No chunks from PDF '{pdf_path}'.")
        return

    texts = [c["text"] for c in chunks]
    embeddings = await _embed_texts_ollama(texts)

    ids, valid_embeddings, docs, metas = [], [], [], []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        if not emb:
            continue
        chunk_id = f"pdf-{_content_hash(chunk['text'])}-p{chunk['page']}-{i}"
        ids.append(chunk_id)
        valid_embeddings.append(emb)
        docs.append(chunk["text"])
        metas.append(
            {
                "source": chunk.get("source", pdf_path),
                "page": chunk.get("page", 0),
                "total_pages": chunk.get("total_pages", 0),
                "type": "pdf",
                **task.metadata,
            }
        )

    if not ids:
        return

    await asyncio.gather(
        db_vector_manager.upsert("pdfs", ids, valid_embeddings, docs, metas),
        *[
            metadata_store.upsert(
                id=id_,
                collection="pdfs",
                source_uri=task.source_uri or pdf_path,
                content_hash=_content_hash(doc),
                status="indexed",
            )
            for id_, doc in zip(ids, docs)
        ],
    )
    _log("success", f"[PDFWorker] Indexed {len(ids)} chunks from '{pdf_path}'.")


async def _process_image(
    task: IngestionTask,
    executor: ThreadPoolExecutor,
) -> None:
    """Embed via SigLIP (ONNX in thread) → write ChromaDB + SQLite."""
    _log(
        "info",
        f"[ImageWorker] Processing image task {task.task_id}: '{task.source_uri}'",
    )

    try:
        embedding = await _embed_image_siglip(task.content, executor)
    except Exception as exc:
        _log("error", f"[ImageWorker] SigLIP embed failed: {exc}", "moderate")
        return

    if not embedding:
        _log("warning", f"[ImageWorker] Empty embedding for '{task.source_uri}'.")
        return

    chunk_id = f"img-{_content_hash(task.content)}"
    meta = {
        "source": task.source_uri,
        "type": "image",
        **task.metadata,
    }

    await asyncio.gather(
        db_vector_manager.upsert(
            "images",
            ids=[chunk_id],
            embeddings=[embedding],
            documents=[task.source_uri],
            metadatas=[meta],
        ),
        metadata_store.upsert(
            id=chunk_id,
            collection="images",
            source_uri=task.source_uri,
            content_hash=_content_hash(task.content),
            status="indexed",
        ),
    )
    _log("success", f"[ImageWorker] Indexed image '{task.source_uri}'.")


async def _process_custom(
    task: IngestionTask,
    executor: ThreadPoolExecutor,
) -> None:
    """Generic text ingestion → embed (Ollama) → write ChromaDB + SQLite."""
    _log("info", f"[CustomWorker] Processing custom task {task.task_id}")

    chunks = MarkdownChunker.chunk(str(task.content), source_uri=task.source_uri)
    if not chunks:
        return

    texts = [c["text"] for c in chunks]
    embeddings = await _embed_texts_ollama(texts)

    ids, valid_embeddings, docs, metas = [], [], [], []
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        if not emb:
            continue
        chunk_id = f"custom-{_content_hash(chunk['text'])}-{i}"
        ids.append(chunk_id)
        valid_embeddings.append(emb)
        docs.append(chunk["text"])
        metas.append(
            {
                "source": task.source_uri,
                "type": "custom",
                **task.metadata,
            }
        )

    if not ids:
        return

    await asyncio.gather(
        db_vector_manager.upsert("custom", ids, valid_embeddings, docs, metas),
        *[
            metadata_store.upsert(
                id=id_,
                collection="custom",
                source_uri=task.source_uri,
                content_hash=_content_hash(doc),
                status="indexed",
            )
            for id_, doc in zip(ids, docs)
        ],
    )
    _log("success", f"[CustomWorker] Indexed {len(ids)} chunks.")


# ===========================================================================
# IngestionService
# ===========================================================================

_PROCESSORS = {
    "websites": _process_website,
    "pdfs": _process_pdf,
    "images": _process_image,
    "custom": _process_custom,
}


class IngestionService:
    """
    Manages a background worker pool fed by a priority queue.

    Usage
    -----
    ::

        service = IngestionService()
        await service.start()

        await service.submit(IngestionTask(
            priority   = Priority.HIGH,
            collection = "websites",
            content    = "<markdown text>",
            source_uri = "https://example.com",
        ))

        await service.stop()

    The service also integrates with the project's `scheduler` for fire-and-forget
    background submissions (see ``submit_via_scheduler``).
    """

    def __init__(self, worker_count: int = WORKER_COUNT) -> None:
        self._queue: asyncio.PriorityQueue[IngestionTask] = asyncio.PriorityQueue()
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix="siglip_onnx",
        )
        self._worker_count = worker_count
        self._workers: List[asyncio.Task] = []
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker_loop(worker_id=i))
            for i in range(self._worker_count)
        ]
        _log("info", f"IngestionService started with {self._worker_count} workers.")

    async def stop(self) -> None:
        """Drain the queue then shut down workers gracefully."""
        _log("info", "IngestionService stopping — draining queue…")
        await self._queue.join()
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._executor.shutdown(wait=False)
        _log("info", "IngestionService stopped.")

    # ------------------------------------------------------------------
    # Public submission API
    # ------------------------------------------------------------------

    async def submit(self, task: IngestionTask) -> str:
        """Enqueue a task. Returns the task_id for tracking."""
        await metadata_store.upsert(
            id=task.task_id,
            collection=task.collection,
            source_uri=task.source_uri,
            status="pending",
        )
        await self._queue.put(task)
        _log(
            "info",
            f"Task {task.task_id} queued → '{task.collection}' (priority={task.priority})",
        )
        return task.task_id

    async def submit_via_scheduler(self, task: IngestionTask) -> str:
        """
        Submit via the project's task_scheduler for true fire-and-forget
        background scheduling outside the current event loop context.
        """
        await scheduler.schedule(
            self.submit,
            params={"task": task},
        )
        return task.task_id

    # ------------------------------------------------------------------
    # Worker loop
    # ------------------------------------------------------------------

    async def _worker_loop(self, worker_id: int) -> None:
        _log("info", f"Worker-{worker_id} started.")
        while self._running:
            try:
                task: IngestionTask = await asyncio.wait_for(
                    self._queue.get(), timeout=2.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            processor = _PROCESSORS.get(task.collection)
            if processor is None:
                _log(
                    "error",
                    f"Worker-{worker_id}: unknown collection '{task.collection}'.",
                    "moderate",
                )
                self._queue.task_done()
                continue

            try:
                await metadata_store.mark_status(task.task_id, "processing")
                await processor(task, self._executor)
                await metadata_store.mark_status(task.task_id, "indexed")
            except Exception as exc:
                _log(
                    "error",
                    f"Worker-{worker_id} failed on task {task.task_id}: {exc}",
                    "moderate",
                )
                await metadata_store.mark_status(task.task_id, "error")
            finally:
                self._queue.task_done()

        _log("info", f"Worker-{worker_id} exited.")


# ===========================================================================
# Convenience factory function
# ===========================================================================


def make_task(
    collection: str,
    content: Any,
    source_uri: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    priority: int = Priority.NORMAL,
) -> IngestionTask:
    """Thin helper so callers don't need to import the dataclass directly."""
    return IngestionTask(
        priority=priority,
        collection=collection,
        content=content,
        source_uri=source_uri,
        metadata=metadata or {},
    )


# Singleton — start() must be called by the application bootstrap
ingestion_service = IngestionService()
