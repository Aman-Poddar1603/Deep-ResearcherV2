import json

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from sse.event_bus import event_bus

app = FastAPI()


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
