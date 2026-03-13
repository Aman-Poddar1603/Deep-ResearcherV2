import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class HistoryType(str, Enum):
    EXPORT = ("export",)
    RESEARCH = ("research",)
    CHAT = "chat"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    GENERATION = "generation"


class HistoryActions(str, Enum):
    DELETE = "delete"


class HistoryItem(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="The unique identifier of the history item",
    )
    title: str = Field(..., description="The title of the history item")
    is_file: bool = Field(..., description="Whether the history item is a file")
    file_type: str = Field(..., description="The type of the file")
    file_size: int = Field(..., description="The size of the file in bytes")
    is_deleted: bool = Field(..., description="Whether the history item is deleted")
    description: str = Field(..., description="The description of the history item")
    type: HistoryType = Field(..., description="The type of the history item")
    created_at: datetime = Field(
        ..., description="The time the history item was created"
    )
    action: HistoryActions = Field(
        ..., description="The action performed on the history item"
    )


class HistoryItemResponse(BaseModel):
    history_items: list[HistoryItem] = Field(
        ..., description="The list of history items"
    )
    page: int = Field(..., description="The current page number")
    total_pages: int = Field(..., description="The total number of pages")
    offset: int = Field(..., description="The offset of the first item on the page")
