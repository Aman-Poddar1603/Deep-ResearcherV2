from datetime import datetime
from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, status

from main.apis.models.chats import (
    ChatAttachmentCreate,
    ChatAttachmentListResponse,
    ChatAttachmentPatch,
    ChatAttachmentRecord,
    ChatMessageCreate,
    ChatMessageListResponse,
    ChatMessagePatch,
    ChatMessageRecord,
    ChatThreadCreate,
    ChatThreadListResponse,
    ChatThreadPatch,
    ChatThreadRecord,
)
from main.src.chat import chat_orchestrator

router = APIRouter(prefix="/chats", tags=["chats"])

chat_view = chat_orchestrator.ChatOrchestrator()


def _raise_chat_http_error(action: str, exc: Exception) -> NoReturn:
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


@router.get("/threads", response_model=ChatThreadListResponse)
def list_threads(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    workspace_id: str | None = Query(default=None, alias="workspaceId"),
    user_id: str | None = Query(default=None, alias="userId"),
    created_by: str | None = Query(default=None, alias="createdBy"),
    is_pinned: bool | None = Query(default=None, alias="isPinned"),
    thread_title_contains: str | None = Query(
        default=None, alias="threadTitleContains"
    ),
    sort_by: Literal[
        "updated_at", "created_at", "thread_title", "pinned_order"
    ] = Query(default="updated_at", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> ChatThreadListResponse:
    try:
        return chat_view.listThreads(
            page=page,
            size=size,
            workspace_id=workspace_id,
            user_id=user_id,
            created_by=created_by,
            is_pinned=is_pinned,
            thread_title_contains=thread_title_contains,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_chat_http_error("List chat threads", exc)


@router.get("/threads/{thread_id}", response_model=ChatThreadRecord)
def get_thread(thread_id: str) -> ChatThreadRecord:
    try:
        return chat_view.getThread(thread_id)
    except Exception as exc:
        _raise_chat_http_error(f"Fetch chat thread {thread_id}", exc)


@router.post(
    "/threads", response_model=ChatThreadRecord, status_code=status.HTTP_201_CREATED
)
def create_thread(payload: ChatThreadCreate) -> ChatThreadRecord:
    try:
        return chat_view.createThread(payload)
    except Exception as exc:
        _raise_chat_http_error("Create chat thread", exc)


@router.put("/threads/{thread_id}", response_model=ChatThreadRecord)
def replace_thread(thread_id: str, payload: ChatThreadCreate) -> ChatThreadRecord:
    try:
        return chat_view.updateThread(thread_id, payload)
    except Exception as exc:
        _raise_chat_http_error(f"Replace chat thread {thread_id}", exc)


@router.patch("/threads/{thread_id}", response_model=ChatThreadRecord)
def patch_thread(thread_id: str, payload: ChatThreadPatch) -> ChatThreadRecord:
    try:
        return chat_view.patchThread(thread_id, payload)
    except Exception as exc:
        _raise_chat_http_error(f"Patch chat thread {thread_id}", exc)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: str) -> Response:
    try:
        chat_view.deleteThread(thread_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_chat_http_error(f"Delete chat thread {thread_id}", exc)


@router.get("/messages", response_model=ChatMessageListResponse)
def list_messages(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    thread_id: str | None = Query(default=None, alias="threadId"),
    role: str | None = Query(default=None),
    parent_id: str | None = Query(default=None, alias="parentId"),
    content_contains: str | None = Query(default=None, alias="contentContains"),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    sort_by: Literal["message_seq", "created_at", "updated_at"] = Query(
        default="message_seq", alias="sortBy"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="asc", alias="sortOrder"),
) -> ChatMessageListResponse:
    try:
        return chat_view.listMessages(
            page=page,
            size=size,
            thread_id=thread_id,
            role=role,
            parent_id=parent_id,
            content_contains=content_contains,
            created_from=created_from,
            created_to=created_to,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_chat_http_error("List chat messages", exc)


@router.get("/messages/{message_id}", response_model=ChatMessageRecord)
def get_message(message_id: str) -> ChatMessageRecord:
    try:
        return chat_view.getMessage(message_id)
    except Exception as exc:
        _raise_chat_http_error(f"Fetch chat message {message_id}", exc)


@router.post(
    "/messages", response_model=ChatMessageRecord, status_code=status.HTTP_201_CREATED
)
def create_message(payload: ChatMessageCreate) -> ChatMessageRecord:
    try:
        return chat_view.createMessage(payload)
    except Exception as exc:
        _raise_chat_http_error("Create chat message", exc)


@router.patch("/messages/{message_id}", response_model=ChatMessageRecord)
def patch_message(message_id: str, payload: ChatMessagePatch) -> ChatMessageRecord:
    try:
        return chat_view.patchMessage(message_id, payload)
    except Exception as exc:
        _raise_chat_http_error(f"Patch chat message {message_id}", exc)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: str) -> Response:
    try:
        chat_view.deleteMessage(message_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_chat_http_error(f"Delete chat message {message_id}", exc)


@router.get("/attachments", response_model=ChatAttachmentListResponse)
def list_attachments(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    message_id: str | None = Query(default=None, alias="messageId"),
    attachment_type: str | None = Query(default=None, alias="attachmentType"),
    min_attachment_size: int | None = Query(
        default=None, alias="minAttachmentSize", ge=0
    ),
    max_attachment_size: int | None = Query(
        default=None, alias="maxAttachmentSize", ge=0
    ),
    path_contains: str | None = Query(default=None, alias="pathContains"),
    sort_by: Literal["created_at", "updated_at", "attachment_size"] = Query(
        default="created_at", alias="sortBy"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sortOrder"),
) -> ChatAttachmentListResponse:
    try:
        return chat_view.listAttachments(
            page=page,
            size=size,
            message_id=message_id,
            attachment_type=attachment_type,
            min_attachment_size=min_attachment_size,
            max_attachment_size=max_attachment_size,
            path_contains=path_contains,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_chat_http_error("List chat attachments", exc)


@router.get("/attachments/{attachment_id}", response_model=ChatAttachmentRecord)
def get_attachment(attachment_id: str) -> ChatAttachmentRecord:
    try:
        return chat_view.getAttachment(attachment_id)
    except Exception as exc:
        _raise_chat_http_error(f"Fetch chat attachment {attachment_id}", exc)


@router.post(
    "/attachments",
    response_model=ChatAttachmentRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_attachment(payload: ChatAttachmentCreate) -> ChatAttachmentRecord:
    try:
        return chat_view.createAttachment(payload)
    except Exception as exc:
        _raise_chat_http_error("Create chat attachment", exc)


@router.patch("/attachments/{attachment_id}", response_model=ChatAttachmentRecord)
def patch_attachment(
    attachment_id: str, payload: ChatAttachmentPatch
) -> ChatAttachmentRecord:
    try:
        return chat_view.patchAttachment(attachment_id, payload)
    except Exception as exc:
        _raise_chat_http_error(f"Patch chat attachment {attachment_id}", exc)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(attachment_id: str) -> Response:
    try:
        chat_view.deleteAttachment(attachment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        _raise_chat_http_error(f"Delete chat attachment {attachment_id}", exc)
