"""
WSEmitter — the single point of contact for sending events to the frontend.

Every event goes through here. It:
  1. Publishes to Redis pub/sub (for reconnect relay).
  2. Sends directly to the active WebSocket (if connected).
"""
import json
import logging
from typing import TYPE_CHECKING

from fastapi import WebSocket

from research.models import WSEvent
from research.session import publish_event

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class WSEmitter:
    def __init__(self, research_id: str, websocket: WebSocket | None = None):
        self.research_id = research_id
        self._ws = websocket

    def attach(self, websocket: WebSocket) -> None:
        self._ws = websocket

    def detach(self) -> None:
        self._ws = None

    async def emit(self, event: WSEvent) -> None:
        payload = event.to_dict()
        # Always publish to Redis for reconnect/relay
        await publish_event(self.research_id, payload)
        # Send directly to WS if connected
        if self._ws:
            try:
                await self._ws.send_text(json.dumps(payload))
            except Exception as exc:
                logger.warning("[emitter] WS send failed (%s): %s", self.research_id, exc)
                self._ws = None

    async def emit_raw(self, payload: dict) -> None:
        await publish_event(self.research_id, payload)
        if self._ws:
            try:
                await self._ws.send_text(json.dumps(payload))
            except Exception as exc:
                logger.warning("[emitter] WS send failed (%s): %s", self.research_id, exc)
                self._ws = None
