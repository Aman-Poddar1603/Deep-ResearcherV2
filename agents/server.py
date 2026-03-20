import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

from sse.event_bus import event_bus
from utils.task_scheduler import scheduler
from web.web_crawler import close_crawler_engine, init_crawler_engine
from web.scraper import read_pages, search_and_scrape_pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------- SERVER START --------
    await scheduler.start()
    await init_crawler_engine(batch_size=10, concurrency=8)

    yield

    # -------- SERVER SHUTDOWN --------
    await close_crawler_engine()
    await scheduler.shutdown()


app = FastAPI(title="Agent Server DRv2!", version="1.0.0", lifespan=lifespan)

# Include the scheme (http) and port. Add 127.0.0.1 as well if needed.
allowed_origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
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


class ScrapeUrlsRequest(BaseModel):
    urls: list[str]
    max_urls: int | None = None
    max_concurrent_scrape_batches: int = 3
    origin_research_id: str | None = None


class SearchScrapeRequest(BaseModel):
    query: str
    # Cap for how many search result URLs we want to scrape.
    # If SearXNG returns fewer than this number, we scrape all returned URLs.
    max_no_url: int | None = None
    max_concurrent_scrape_batches: int = 3
    origin_research_id: str | None = None


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


@app.post("/scrape/urls")
async def scrape_urls(req: ScrapeUrlsRequest):
    """
    Test endpoint: send a list of URLs, receive scraped items streamed as SSE.

    Body example:
      {
        "urls": ["https://example.com"],
        "max_urls": null,
        "max_concurrent_scrape_batches": 3,
        "origin_research_id": null
      }
    """

    async def event_generator():
        yield format_sse(
            {
                "success": True,
                "type": "start",
                "message": f"Starting scrape of {len(req.urls)} urls",
            }
        )

        try:
            async for item in read_pages(
                req.urls,
                max_urls=req.max_urls,
                max_concurrent_scrape_batches=req.max_concurrent_scrape_batches,
                origin_research_id=req.origin_research_id,
            ):
                yield format_sse(item)
            yield format_sse(
                {
                    "success": True,
                    "type": "done",
                    "message": f"Finished scraping {len(req.urls)} urls",
                }
            )
        except Exception as e:
            yield format_sse(
                {
                    "success": False,
                    "type": "error",
                    "message": str(e),
                }
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/scrape/search")
async def scrape_search(req: SearchScrapeRequest):
    """
    Search URLs with SearXNG, then scrape them (crawl4ai).

    Semantics:
    - If `max_no_url` is set, we scrape up to that many URLs.
    - If the search returns fewer than `max_no_url`, we scrape all returned URLs.

    SSE response (text/event-stream):
    - type: "start"
    - then one scraped item per `data:` event
    - type: "done" at the end
    """

    async def event_generator():
        yielded_items = 0
        yield format_sse(
            {
                "success": True,
                "type": "start",
                "message": f"Searching & scraping for query: {req.query}",
            }
        )

        try:
            async for item in search_and_scrape_pages(
                [req.query],
                max_urls=req.max_no_url,
                max_concurrent_scrape_batches=req.max_concurrent_scrape_batches,
                queries_are_urls=False,
                origin_research_id=req.origin_research_id,
            ):
                yielded_items += 1
                yield format_sse(item)

            yield format_sse(
                {
                    "success": True,
                    "type": "done",
                    "message": (
                        f"Finished search+scrape stream. "
                        f"Yielded {yielded_items} scrape item(s)."
                    ),
                    "yielded_items": yielded_items,
                }
            )
        except Exception as e:
            yield format_sse(
                {
                    "success": False,
                    "type": "error",
                    "message": str(e),
                }
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
