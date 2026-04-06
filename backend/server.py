"""
This is the main entry point for the Deep Researcher v2 API.
It is used to start and stop the background workers.
"""

from contextlib import asynccontextmanager
import json
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from main.apis.bucket.bucket_urls import router as bucket_router
from main.apis.chats.chat_urls import router as chats_router
from main.apis.history.history_urls import router as history_router
import main.apis.reasearch.research_urls as research_urls
from main.apis.settings.settings_urls import router as settings_router
from main.apis.workspace.workspace_urls import router as workspace_router
from main.src.research.layer2.tools import shutdown_mcp_runtime
from main.src.research.router import router as research_runtime_router
from main.src.utils.core.task_schedular import scheduler
from main.sse.event_bus import event_bus

research_router = getattr(research_urls, "router")
logger = logging.getLogger(__name__)

# Initilize the queue workers: queue system for entire application so add temprory non important task to background processing queue.


@asynccontextmanager
async def lifespan(app: FastAPI):
    """A context manager for the FastAPI application lifespan.
    It is used to start and stop the background workers.
    """
    # -------- SERVER START --------
    await scheduler.start()

    yield

    # -------- SERVER SHUTDOWN --------
    await scheduler.shutdown()
    try:
        await shutdown_mcp_runtime()
    except Exception as exc:
        logger.warning("Failed to close MCP runtime cleanly: %s", exc)


app = FastAPI(
    title="Deep Research Agent API",
    version="1.0.0",
    description="""
## Deep Research Agent API

The backend exposes the research workflow through:

1. `POST /research/start` to allocate a research session.
2. `WS /research/ws/{research_id}` to stream interactive research events.
3. `POST /research/{research_id}/stop` for a graceful shutdown.
4. `GET /research/{research_id}/status` for polling session state.
""",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include the scheme (http) and port. Add 127.0.0.1 as well if needed.
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]

# Register CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # or ["*"] for all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_sse(data: dict):
    return f"data: {json.dumps(data)}\n\n"


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/research/events", tags=["research"], response_class=JSONResponse)
async def research_event_catalogue() -> dict[str, object]:
    return {
        "base_fields": {
            "event": "string",
            "research_id": "string",
            "ts": "ISO 8601 UTC timestamp",
        },
        "groups": {
            "input": [
                "input.validated",
                "input.qa_question",
                "input.plan_ready",
                "input.approved",
            ],
            "plan": [
                "plan.step_started",
                "plan.step_completed",
                "plan.step_failed",
                "plan.all_done",
            ],
            "tool": ["tool.called", "tool.result", "tool.error"],
            "think": ["think.chunk", "think.done"],
            "react": ["react.reason", "react.act", "react.observe"],
            "artifact": ["artifact.chunk", "artifact.done"],
            "tokens": ["tokens.update"],
            "stop": ["stop.requested", "stop.flushing", "stop.saved"],
            "system": ["system.progress", "system.error", "system.reconnected"],
        },
    }


@app.get("/research/ws-protocol", tags=["research"], response_class=JSONResponse)
async def research_ws_protocol() -> dict[str, object]:
    return {
        "direction": "frontend -> backend",
        "format": "JSON text frame over WebSocket",
        "messages": {
            "user.answer": {
                "type": "user.answer",
                "answer": "string",
            },
            "user.approval": {
                "type": "user.approval",
                "action": "approve | refactor",
                "feedback": "string, required when action is refactor",
            },
            "stop.request": {
                "type": "stop.request",
            },
        },
    }


@app.get("/events/{client_id}")
async def stream(request: Request, client_id: str):
    queue = event_bus.register(client_id)

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break

                data = await queue.get()
                yield format_sse(data)

        finally:
            event_bus.unregister(client_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


app.include_router(research_router)
app.include_router(research_runtime_router, prefix="/research")
app.include_router(workspace_router)
app.include_router(history_router)
app.include_router(chats_router)
app.include_router(bucket_router)
app.include_router(settings_router)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=1)
