import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from sse.event_bus import event_bus
from utils.task_scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------- SERVER START --------
    await scheduler.start()

    yield

    # -------- SERVER SHUTDOWN --------
    await scheduler.shutdown()


app = FastAPI(title="Agent Server DRv2!", version="1.0.0", lifespan=lifespan)


def format_sse(data: dict):
    return f"data: {json.dumps(data)}\n\n"


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
