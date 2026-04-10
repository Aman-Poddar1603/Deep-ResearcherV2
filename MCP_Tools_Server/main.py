import json
import logging
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from src import (
    get_youtube_data,
    process_files,
    read_pages,
    search_and_scrape_pages,
    search_images,
    search_urls,
    understand_images,
)
from src.web.web_crawler import init_crawler_engine
from sse.event_bus import event_bus
from utils.logger.AgentLogger import quickLog
from utils.task_scheduler import scheduler

# 🔥 Logging Setup (REAL server vibes)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("MCP-Server")

# Global flag to ensure initialization only once
initialized = False


# ─────────────────────────── LIFESPAN ──────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastMCP):
    global initialized
    # -------- SERVER START --------
    if not initialized:
        await scheduler.start()
        await init_crawler_engine(batch_size=10, concurrency=8)
        initialized = True

    yield

    # -------- SERVER SHUTDOWN --------
    # Removed closes to allow persistence across sessions


mcp_server = FastMCP(
    name="Deep Researcher v2 Agent MCP Tools",
    host="0.0.0.0",
    port=8001,
    lifespan=lifespan,
)

# ========================
# 🧰 TOOLS
# ========================


@mcp_server.tool(
    name="web_search",
    title="Searches the web for a query and scrapes relevant pages.",
    description="Input: string query (e.g., 'latest AI news'). Output: JSON string with {'results': [list of dicts containing page details]}.",
)
async def web_search(query: str):
    quickLog(f"Searching web: {query}", "info", module="CRAWLER")

    await event_bus.broadcast({"type": "search", "query": query})

    results = [item async for item in search_and_scrape_pages([query])]

    return json.dumps({"results": results})


@mcp_server.tool(
    name="read_webpages",
    title="Scrapes a list of provided URLs.",
    description="Input: list[str] urls (e.g., ['https://example.com/page1', 'https://example.com/page2']). Output: JSON string with {'results': [list of dicts containing page details]}.",
)
async def read_webpages(urls: list[str]):
    quickLog(f"Reading pages: {len(urls)} URLs", "info", module="CRAWLER")

    return json.dumps({"results": [item async for item in read_pages(urls)]})


@mcp_server.tool(
    name="youtube_search",
    title="Searches YouTube for videos matching a query.",
    description="Input: str query (e.g., 'black hole mystery'). Output: JSON string with dict containing query, total_results, scrape_time, and list of video details.",
)
async def youtube_search(query: str):
    quickLog(f"YouTube search: {query}", "info", module="AGENTS")

    return json.dumps(await get_youtube_data(query))


@mcp_server.tool(
    name="image_search_tool",
    title="Searches images on internet and give the images in list.",
    description="Input: list[tuple[str, int]] queries (e.g., [('apple images', 10)]). Output: JSON string with dict mapping query to list of image URLs.",
)
async def image_search_tool(queries: list[tuple[str, int]]):
    quickLog(f"Image search: {queries}", "info", module="AGENTS")

    return json.dumps(await search_images(queries))


@mcp_server.tool(
    name="understand_images_tool",
    title="Analyzes images using AI to generate titles and descriptions.",
    description="Input: list[str] paths (e.g., ['https://example.com/image.jpg', '/local/path/image.png']). Output: JSON string with dict containing total_files, success_count, tokens_used, time_taken, and content (dict filename to analysis).",
)
async def understand_images_tool(paths: list[str]):
    quickLog(f"Understanding {len(paths)} images", "info", module="AI")

    return json.dumps(await understand_images(paths))


@mcp_server.tool(
    name="process_docs",
    title="Processes documents and summarizes them using AI.",
    description="Input: list[str] paths (e.g., ['https://example.com/doc.pdf', '/local/path/doc.docx']). Output: JSON string with dict containing total_files, success_count, tokens_used, time_taken, and content (dict filename to summary).",
)
async def process_docs(paths: list[str]):
    quickLog(f"Processing docs: {paths}", "info", module="UTILS")

    return json.dumps(await process_files(paths, "http://localhost:11434"))


@mcp_server.tool(
    name="search_urls_tool",
    title="Searches for URLs related to a query without scraping.",
    description="Input: str query (e.g., 'latest AI news'). Output: JSON string list of unique URLs.",
)
async def search_urls_tool(query: str):
    quickLog(f"Searching URLs for: {query}", "info", module="CRAWLER")

    return json.dumps(await search_urls([query]))


@mcp_server.tool(
    name="scrape_single_url",
    title="Scrapes a single URL and returns its details.",
    description="Input: str url (e.g., 'https://example.com/page'). Output: JSON string with {'results': [dict containing page details]}.",
)
async def scrape_single_url(url: str):
    quickLog(f"Scraping single URL: {url}", "info", module="CRAWLER")

    return json.dumps({"results": [item async for item in read_pages([url])]})


# ========================
# 🏁 ENTRY POINT
# ========================


def main():
    logger.info("🔥 Starting MCP Tools Server on port 8001")
    mcp_server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
