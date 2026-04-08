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
from research.session import append_event, publish_event

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
        event_id: str | None = None

        # Persist first so reconnect clients can replay missed events.
        try:
            event_id = await append_event(self.research_id, payload)
            if event_id:
                payload.setdefault("event_id", event_id)
        except Exception as exc:
            logger.warning(
                "[emitter] event stream append failed (%s): %s", self.research_id, exc
            )

        # Publish for compatibility with existing live subscribers.
        try:
            await publish_event(self.research_id, payload)
        except Exception as exc:
            logger.warning(
                "[emitter] pubsub publish failed (%s): %s", self.research_id, exc
            )

        # Send directly to WS if connected
        if self._ws:
            try:
                await self._ws.send_text(json.dumps(payload))
            except Exception as exc:
                logger.warning(
                    "[emitter] WS send failed (%s): %s", self.research_id, exc
                )
                self._ws = None

    async def emit_raw(self, payload: dict) -> None:
        event_id: str | None = None
        try:
            event_id = await append_event(self.research_id, payload)
            if event_id:
                payload.setdefault("event_id", event_id)
        except Exception as exc:
            logger.warning(
                "[emitter] event stream append failed (%s): %s", self.research_id, exc
            )

        try:
            await publish_event(self.research_id, payload)
        except Exception as exc:
            logger.warning(
                "[emitter] pubsub publish failed (%s): %s", self.research_id, exc
            )

        if self._ws:
            try:
                await self._ws.send_text(json.dumps(payload))
            except Exception as exc:
                logger.warning(
                    "[emitter] WS send failed (%s): %s", self.research_id, exc
                )
                self._ws = None
