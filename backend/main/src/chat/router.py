"""
Chat runtime router.

Exposes WebSocket streaming for live chat turns while keeping CRUD REST APIs in
main.apis.chats.chat_urls.
"""

from fastapi import APIRouter, WebSocket

from main.src.chat.websocket_handler import handle_chat_websocket

router = APIRouter(tags=["chats"])


@router.websocket("/threads/{thread_id}/ws")
async def chat_websocket(websocket: WebSocket, thread_id: str) -> None:
    await handle_chat_websocket(websocket, thread_id)
