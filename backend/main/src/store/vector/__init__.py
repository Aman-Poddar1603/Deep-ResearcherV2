"""
store/__init__.py — Deep Researcher v2 vector store package.

Public singletons
-----------------
    db_vector_manager   : DBVectorManager   — collection-agnostic ChromaDB CRUD
    sqlite_meta_store   : SQLiteMetaStore   — WAL SQLite3 metadata side-car
    ingestion_service   : IngestionService  — async background ingestion pipeline
    search_engine       : SearchEngine      — parallel multi-collection search

Typical startup sequence
------------------------
    from main.src.store import ingestion_service, search_engine

    await ingestion_service.start(num_workers=4)

    # Ingest
    await ingestion_service.ingest_website(url, markdown_content)
    await ingestion_service.ingest_pdf("/path/to/paper.pdf")
    await ingestion_service.ingest_image("/path/to/photo.jpg", label="diagram")
    await ingestion_service.ingest_custom(text="Raw note", source="user")

    # Search
    ctx = await search_engine.search("transformer architectures", n_results=10)
    img_ctx = await search_engine.search_by_image("/path/to/query.jpg")

    # Shutdown
    await ingestion_service.stop()
    await search_engine.close()
"""

from main.src.store.vector.DBVector import (
    DBVectorManager,
    MetadataStore,
    db_vector_manager,
    metadata_store,
    COLLECTIONS,
    _CHROMA_PATH,
    _SQLITE_PATH,
)

from main.src.store.vector.IngestionService import (
    IngestionService,
    IngestionTask,
    Priority,
    ingestion_service,
)

from main.src.store.vector.SearchEngine import (
    SearchEngine,
    search_engine,
)

__all__ = [
    # Singletons
    "db_vector_manager",
    "metadata_store",
    "ingestion_service",
    "search_engine",
    # Classes
    "DBVectorManager",
    "MetadataStore",
    "IngestionService",
    "IngestionTask",
    "SearchEngine",
    # Constants
    "COLLECTIONS",
    "Priority",
    "_CHROMA_PATH",
    "_SQLITE_PATH",
]
