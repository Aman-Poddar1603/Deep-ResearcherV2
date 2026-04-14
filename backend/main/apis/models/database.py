from typing import Any, Literal

from pydantic import BaseModel, Field


DatabaseType = Literal["standard", "vector"]
DatabaseStatus = Literal["active", "syncing", "idle"]


class DatabaseListItem(BaseModel):
    id: str
    name: str
    description: str
    type: DatabaseType
    color: str
    status: DatabaseStatus
    tableCount: int
    totalRows: int
    size: str
    lastModified: str
    engine: str
    version: str


class TableMeta(BaseModel):
    name: str
    rows: int
    columns: int
    size: str
    lastModified: str
    description: str = ""


class DatabaseDetail(BaseModel):
    id: str
    name: str
    description: str
    type: DatabaseType
    color: str
    status: DatabaseStatus
    tables: list[TableMeta] = Field(default_factory=list)
    totalSize: str
    createdAt: str
    lastModified: str
    engine: str
    version: str
    tableCount: int
    totalRows: int


class DatabaseListResponse(BaseModel):
    items: list[DatabaseListItem]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


class DatabaseTableListResponse(BaseModel):
    items: list[TableMeta]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int


class TableColumnMeta(BaseModel):
    cid: int | None = None
    name: str
    type: str | None = None
    notnull: bool = False
    defaultValue: Any = None
    pk: bool = False


class TableRowsResponse(BaseModel):
    databaseId: str
    tableName: str
    columns: list[TableColumnMeta]
    items: list[dict[str, Any]]
    page: int
    size: int
    total_items: int
    total_pages: int
    offset: int
