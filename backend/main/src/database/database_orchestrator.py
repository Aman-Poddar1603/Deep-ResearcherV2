import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from main.apis.models.database import (
    DatabaseDetail,
    DatabaseListItem,
    DatabaseListResponse,
    DatabaseTableListResponse,
    TableColumnMeta,
    TableMeta,
    TableRowsResponse,
)
from main.src.store.DBManager import (
    buckets_db_manager,
    chats_db_manager,
    history_db_manager,
    logs_db_manager,
    main_db_manager,
    researches_db_manager,
    scrapes_db_manager,
)

try:
    import chromadb

    from main.src.store.vector.DBVector import (
        COLLECTIONS,
        _CHROMA_PATH,
        db_vector_manager,
    )

    VECTOR_ENABLED = True
    CHROMA_VERSION = getattr(chromadb, "__version__", "unknown")
except Exception:  # pylint: disable=broad-except
    COLLECTIONS = tuple()
    db_vector_manager = None
    _CHROMA_PATH = ""
    VECTOR_ENABLED = False
    CHROMA_VERSION = "unavailable"


class DatabaseOrchestrator:
    def __init__(self):
        self._sqlite_registry: Dict[str, Dict[str, Any]] = {
            "main": {
                "manager": main_db_manager,
                "name": "Basic",
                "description": "Core application data and user preferences",
                "color": "blue-400",
            },
            "history": {
                "manager": history_db_manager,
                "name": "History",
                "description": "Activity logs, actions, and audit trails",
                "color": "purple-400",
            },
            "scrapes": {
                "manager": scrapes_db_manager,
                "name": "Scrapes",
                "description": "Web scraping results and extracted data",
                "color": "green-400",
            },
            "researches": {
                "manager": researches_db_manager,
                "name": "Research",
                "description": "Research sessions, sources, and generated artifacts",
                "color": "orange-400",
            },
            "buckets": {
                "manager": buckets_db_manager,
                "name": "Assets",
                "description": "Bucket and asset metadata",
                "color": "pink-400",
            },
            "chats": {
                "manager": chats_db_manager,
                "name": "Chats",
                "description": "Chat threads, messages, and attachments",
                "color": "cyan-400",
            },
            "logs": {
                "manager": logs_db_manager,
                "name": "Logs",
                "description": "System and diagnostics logs",
                "color": "amber-400",
            },
        }

        self._vector_registry: Dict[str, Dict[str, Any]] = {}
        if VECTOR_ENABLED:
            self._vector_registry = {
                "vector_chroma": {
                    "name": "Vector Store",
                    "description": "Chroma vector collections for semantic retrieval",
                    "color": "violet-400",
                }
            }

    @staticmethod
    def _paginate(
        items: list[Any], page: int, size: int
    ) -> tuple[list[Any], int, int, int]:
        safe_page = max(1, int(page))
        safe_size = max(1, int(size))
        total_items = len(items)
        total_pages = ((total_items + safe_size - 1) // safe_size) if total_items else 0
        offset = (safe_page - 1) * safe_size
        return items[offset : offset + safe_size], total_items, total_pages, offset

    @staticmethod
    def _format_bytes(size_bytes: Optional[int]) -> str:
        if size_bytes is None:
            return "-"
        if size_bytes <= 0:
            return "0 B"

        value = float(size_bytes)
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_idx = 0

        while value >= 1024 and unit_idx < len(units) - 1:
            value /= 1024
            unit_idx += 1

        if value >= 10 or unit_idx == 0:
            return f"{value:.0f} {units[unit_idx]}"
        return f"{value:.1f} {units[unit_idx]}"

    @staticmethod
    def _format_relative(ts: Optional[datetime]) -> str:
        if ts is None:
            return "unknown"

        now = datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        seconds = int(max(0, (now - ts).total_seconds()))
        if seconds < 60:
            return f"{seconds} secs ago"
        if seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} mins ago"
        if seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hours ago"
        days = seconds // 86400
        return f"{days} days ago"

    @staticmethod
    def _format_calendar_date(ts: Optional[datetime]) -> str:
        if ts is None:
            return "Unknown"
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.strftime("%b %d, %Y")

    @staticmethod
    def _path_timestamp(path: Path) -> Optional[datetime]:
        try:
            if not path.exists():
                return None
            return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except OSError:
            return None

    @staticmethod
    def _path_created_timestamp(path: Path) -> Optional[datetime]:
        try:
            if not path.exists():
                return None
            return datetime.fromtimestamp(path.stat().st_ctime, tz=timezone.utc)
        except OSError:
            return None

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _serialize_cell_value(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode("utf-8")
            except UnicodeDecodeError:
                return value.hex()
        if isinstance(value, (dict, list)):
            return value
        return str(value)

    def _get_sqlite_entry(self, database_id: str) -> Dict[str, Any]:
        entry = self._sqlite_registry.get(database_id)
        if entry is None:
            raise KeyError(f"Database '{database_id}' not found")
        return entry

    async def _vector_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {name: 0 for name in COLLECTIONS}

        if not VECTOR_ENABLED or db_vector_manager is None:
            return counts

        try:
            health = await db_vector_manager.all_collection_health()
            for collection_name in COLLECTIONS:
                result = health.get(collection_name, {})
                if result.get("success"):
                    data = result.get("data") or {}
                    counts[collection_name] = self._safe_int(
                        data.get("count"), default=0
                    )
        except Exception:  # pylint: disable=broad-except
            pass

        return counts

    def _vector_store_path(self) -> Path:
        if _CHROMA_PATH:
            chroma_path = Path(_CHROMA_PATH)
            if chroma_path.exists():
                return chroma_path

        fallback = Path(__file__).resolve().parents[1] / "store" / "vector" / "chroma"
        return fallback

    def _build_sqlite_tables(self, database_id: str) -> tuple[list[TableMeta], int]:
        entry = self._get_sqlite_entry(database_id)
        manager = entry["manager"]

        table_names_result = manager.list_tables(include_internal=False)
        if not table_names_result.get("success"):
            raise ValueError(
                table_names_result.get("message") or "Failed to list tables"
            )

        table_names = table_names_result.get("data") or []
        db_file_path = Path(manager.db_path)
        db_last_modified = self._format_relative(self._path_timestamp(db_file_path))

        tables: list[TableMeta] = []
        total_rows = 0

        for table_name in table_names:
            schema_result = manager.get_table_schema(table_name)
            if not schema_result.get("success"):
                continue

            count_result = manager.count_rows(table_name)
            if not count_result.get("success"):
                continue

            size_result = manager.get_table_size_bytes(table_name)
            size_bytes = None
            if size_result.get("success"):
                size_bytes = (size_result.get("data") or {}).get("size_bytes")

            row_count = self._safe_int((count_result.get("data") or {}).get("count"))
            column_count = len(schema_result.get("data") or [])
            total_rows += row_count

            tables.append(
                TableMeta(
                    name=table_name,
                    rows=row_count,
                    columns=column_count,
                    size=self._format_bytes(size_bytes),
                    lastModified=db_last_modified,
                    description=f"{table_name} table in {entry['name']} database",
                )
            )

        return tables, total_rows

    async def _build_vector_tables(self) -> tuple[list[TableMeta], int]:
        counts = await self._vector_counts()

        vector_path = self._vector_store_path()
        vector_last_modified = self._format_relative(self._path_timestamp(vector_path))

        tables: list[TableMeta] = []
        total_rows = 0

        for collection_name in COLLECTIONS:
            count = self._safe_int(counts.get(collection_name), default=0)
            total_rows += count
            tables.append(
                TableMeta(
                    name=collection_name,
                    rows=count,
                    columns=3,
                    size="-",
                    lastModified=vector_last_modified,
                    description=f"Vector collection '{collection_name}'",
                )
            )

        return tables, total_rows

    async def _build_sqlite_detail(self, database_id: str) -> DatabaseDetail:
        entry = self._get_sqlite_entry(database_id)
        manager = entry["manager"]
        db_path = Path(manager.db_path)

        tables, total_rows = self._build_sqlite_tables(database_id)
        table_count = len(tables)

        db_size_bytes = 0
        try:
            db_size_bytes = db_path.stat().st_size if db_path.exists() else 0
        except OSError:
            db_size_bytes = 0

        created_at = self._path_created_timestamp(db_path)
        updated_at = self._path_timestamp(db_path)

        return DatabaseDetail(
            id=database_id,
            name=entry["name"],
            description=entry["description"],
            type="standard",
            color=entry["color"],
            status="active",
            tables=tables,
            totalSize=self._format_bytes(db_size_bytes),
            createdAt=self._format_calendar_date(created_at),
            lastModified=self._format_relative(updated_at),
            engine="SQLite",
            version=sqlite3.sqlite_version,
            tableCount=table_count,
            totalRows=total_rows,
        )

    async def _build_vector_detail(self, database_id: str) -> DatabaseDetail:
        if not VECTOR_ENABLED:
            raise KeyError(f"Database '{database_id}' not found")

        entry = self._vector_registry.get(database_id)
        if entry is None:
            raise KeyError(f"Database '{database_id}' not found")

        tables, total_rows = await self._build_vector_tables()
        vector_path = self._vector_store_path()

        size_bytes = 0
        try:
            if vector_path.is_dir():
                size_bytes = sum(
                    file_path.stat().st_size
                    for file_path in vector_path.rglob("*")
                    if file_path.is_file()
                )
            elif vector_path.exists():
                size_bytes = vector_path.stat().st_size
        except OSError:
            size_bytes = 0

        created_at = self._path_created_timestamp(vector_path)
        updated_at = self._path_timestamp(vector_path)

        status: Literal["active", "syncing", "idle"] = "active"
        if total_rows == 0:
            status = "idle"

        return DatabaseDetail(
            id=database_id,
            name=entry["name"],
            description=entry["description"],
            type="vector",
            color=entry["color"],
            status=status,
            tables=tables,
            totalSize=self._format_bytes(size_bytes),
            createdAt=self._format_calendar_date(created_at),
            lastModified=self._format_relative(updated_at),
            engine="ChromaDB",
            version=CHROMA_VERSION,
            tableCount=len(tables),
            totalRows=total_rows,
        )

    async def get_database(self, database_id: str) -> DatabaseDetail:
        if database_id in self._sqlite_registry:
            return await self._build_sqlite_detail(database_id)
        if database_id in self._vector_registry:
            return await self._build_vector_detail(database_id)
        raise KeyError(f"Database '{database_id}' not found")

    async def list_databases(
        self,
        page: int = 1,
        size: int = 50,
        database_type: Optional[Literal["standard", "vector"]] = None,
    ) -> DatabaseListResponse:
        records: list[DatabaseListItem] = []

        for database_id in self._sqlite_registry.keys():
            detail = await self._build_sqlite_detail(database_id)
            records.append(
                DatabaseListItem(
                    id=detail.id,
                    name=detail.name,
                    description=detail.description,
                    type=detail.type,
                    color=detail.color,
                    status=detail.status,
                    tableCount=detail.tableCount,
                    totalRows=detail.totalRows,
                    size=detail.totalSize,
                    lastModified=detail.lastModified,
                    engine=detail.engine,
                    version=detail.version,
                )
            )

        if VECTOR_ENABLED:
            for database_id in self._vector_registry.keys():
                detail = await self._build_vector_detail(database_id)
                records.append(
                    DatabaseListItem(
                        id=detail.id,
                        name=detail.name,
                        description=detail.description,
                        type=detail.type,
                        color=detail.color,
                        status=detail.status,
                        tableCount=detail.tableCount,
                        totalRows=detail.totalRows,
                        size=detail.totalSize,
                        lastModified=detail.lastModified,
                        engine=detail.engine,
                        version=detail.version,
                    )
                )

        if database_type:
            records = [record for record in records if record.type == database_type]

        records.sort(key=lambda item: (item.type, item.name.lower()))

        page_items, total_items, total_pages, offset = self._paginate(
            records, page, size
        )

        return DatabaseListResponse(
            items=page_items,
            page=max(1, int(page)),
            size=max(1, int(size)),
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    async def list_tables(
        self,
        database_id: str,
        page: int = 1,
        size: int = 200,
    ) -> DatabaseTableListResponse:
        detail = await self.get_database(database_id)
        tables = sorted(detail.tables, key=lambda table: table.name.lower())
        page_items, total_items, total_pages, offset = self._paginate(
            tables, page, size
        )

        return DatabaseTableListResponse(
            items=page_items,
            page=max(1, int(page)),
            size=max(1, int(size)),
            total_items=total_items,
            total_pages=total_pages,
            offset=offset,
        )

    async def get_table_rows(
        self,
        database_id: str,
        table_name: str,
        page: int = 1,
        size: int = 25,
        sort_by: Optional[str] = None,
        sort_order: Literal["asc", "desc"] = "asc",
    ) -> TableRowsResponse:
        safe_page = max(1, int(page))
        safe_size = max(1, int(size))

        if database_id in self._sqlite_registry:
            manager = self._sqlite_registry[database_id]["manager"]

            schema_result = manager.get_table_schema(table_name)
            if not schema_result.get("success"):
                raise ValueError(
                    schema_result.get("message") or "Failed to read schema"
                )

            schema_rows = schema_result.get("data") or []
            if not schema_rows:
                raise KeyError(
                    f"Table '{table_name}' not found in database '{database_id}'"
                )

            paginated_result = manager.fetch_paginated(
                table_name=table_name,
                page=safe_page,
                size=safe_size,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            if not paginated_result.get("success"):
                raise ValueError(
                    paginated_result.get("message")
                    or f"Failed to fetch rows from table '{table_name}'"
                )

            payload = paginated_result.get("data") or {}
            raw_items = payload.get("items") or []
            items = [
                {key: self._serialize_cell_value(value) for key, value in row.items()}
                for row in raw_items
            ]

            columns = [
                TableColumnMeta(
                    cid=row.get("cid"),
                    name=row.get("name"),
                    type=row.get("type"),
                    notnull=bool(row.get("notnull")),
                    defaultValue=row.get("dflt_value"),
                    pk=bool(row.get("pk")),
                )
                for row in schema_rows
            ]

            return TableRowsResponse(
                databaseId=database_id,
                tableName=table_name,
                columns=columns,
                items=items,
                page=payload.get("page", safe_page),
                size=payload.get("size", safe_size),
                total_items=payload.get("total_items", 0),
                total_pages=payload.get("total_pages", 0),
                offset=payload.get("offset", 0),
            )

        if database_id in self._vector_registry:
            if not VECTOR_ENABLED or db_vector_manager is None:
                raise ValueError("Vector database is not available in this runtime")

            if table_name not in COLLECTIONS:
                raise KeyError(
                    f"Collection '{table_name}' not found in database '{database_id}'"
                )

            offset = (safe_page - 1) * safe_size
            counts = await self._vector_counts()
            total_items = self._safe_int(counts.get(table_name), default=0)
            total_pages = (
                ((total_items + safe_size - 1) // safe_size) if total_items else 0
            )

            result = await db_vector_manager.fetch_all(
                collection_name=table_name,
                limit=safe_size,
                offset=offset,
            )
            if not result.get("success"):
                raise ValueError(
                    result.get("message")
                    or f"Failed to fetch rows from collection '{table_name}'"
                )

            data = result.get("data") or {}
            ids = list(data.get("ids") or [])
            documents = list(data.get("documents") or [])
            metadatas = list(data.get("metadatas") or [])

            items: list[dict[str, Any]] = []
            for idx, row_id in enumerate(ids):
                doc = documents[idx] if idx < len(documents) else None
                metadata = metadatas[idx] if idx < len(metadatas) else None
                items.append(
                    {
                        "id": row_id,
                        "document": doc,
                        "metadata": metadata,
                    }
                )

            if sort_by in {"id", "document", "metadata"}:
                reverse = sort_order == "desc"

                def _sort_key(item: dict[str, Any]) -> str:
                    value = item.get(sort_by)
                    if isinstance(value, (dict, list)):
                        return json.dumps(value, sort_keys=True)
                    return str(value or "")

                items.sort(key=_sort_key, reverse=reverse)

            columns = [
                TableColumnMeta(cid=0, name="id", type="TEXT", notnull=True, pk=True),
                TableColumnMeta(cid=1, name="document", type="TEXT"),
                TableColumnMeta(cid=2, name="metadata", type="JSON"),
            ]

            return TableRowsResponse(
                databaseId=database_id,
                tableName=table_name,
                columns=columns,
                items=items,
                page=safe_page,
                size=safe_size,
                total_items=total_items,
                total_pages=total_pages,
                offset=offset,
            )

        raise KeyError(f"Database '{database_id}' not found")
