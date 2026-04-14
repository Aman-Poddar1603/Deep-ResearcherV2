from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, status

from main.apis.models.database import (
    DatabaseDetail,
    DatabaseListResponse,
    DatabaseTableListResponse,
    TableRowsResponse,
)
from main.src.database.database_orchestrator import DatabaseOrchestrator

router = APIRouter(prefix="/database", tags=["database"])

database_view = DatabaseOrchestrator()


def _raise_database_http_error(action: str, exc: Exception) -> NoReturn:
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, KeyError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc) or f"Invalid request for {action.lower()}",
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Failed to {action.lower()}",
    ) from exc


@router.get("/", response_model=DatabaseListResponse)
async def list_databases(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=500),
    database_type: Literal["standard", "vector"] | None = Query(
        default=None, alias="type"
    ),
) -> DatabaseListResponse:
    try:
        return await database_view.list_databases(
            page=page,
            size=size,
            database_type=database_type,
        )
    except Exception as exc:
        _raise_database_http_error("List databases", exc)


@router.get("/{database_id}", response_model=DatabaseDetail)
async def get_database(database_id: str) -> DatabaseDetail:
    try:
        return await database_view.get_database(database_id)
    except Exception as exc:
        _raise_database_http_error(f"Fetch database {database_id}", exc)


@router.get("/{database_id}/tables", response_model=DatabaseTableListResponse)
async def list_database_tables(
    database_id: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=200, ge=1, le=1000),
) -> DatabaseTableListResponse:
    try:
        return await database_view.list_tables(database_id, page=page, size=size)
    except Exception as exc:
        _raise_database_http_error(
            f"List tables for database {database_id}",
            exc,
        )


@router.get("/{database_id}/tables/{table_name}/rows", response_model=TableRowsResponse)
async def get_database_table_rows(
    database_id: str,
    table_name: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=25, ge=1, le=500),
    sort_by: str | None = Query(default=None, alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query(default="asc", alias="sortOrder"),
) -> TableRowsResponse:
    try:
        return await database_view.get_table_rows(
            database_id=database_id,
            table_name=table_name,
            page=page,
            size=size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_database_http_error(
            f"Fetch rows for table {table_name} in database {database_id}",
            exc,
        )
