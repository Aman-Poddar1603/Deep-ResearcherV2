# src/agents/webSearchAgent/core/web_crawler.py

import asyncio
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
)

# Helpers (unchanged)
EMPTY_PATTERNS = [
    r"(?i)enable javascript",
    r"(?i)javascript is disabled",
    r"(?i)turn on javascript",
    r"(?i)please wait while your request is being verified",
    r"(?i)loading.*please wait",
]


def _looks_empty_or_blocked(markdown: str | None) -> bool:
    if not markdown:
        return True
    cleaned = markdown.strip()
    if len(cleaned) < 400:
        return True
    for pattern in EMPTY_PATTERNS:
        if re.search(pattern, cleaned):
            return True
    return False


def _normalize_metadata(meta: Optional[dict], url: str) -> Dict[str, Any]:
    if not meta:
        parsed = urlparse(url)
        return {
            "title": None,
            "description": None,
            "banner_image": None,
            "favicon": f"{parsed.scheme}://{parsed.netloc}/favicon.ico",
        }

    icons = meta.get("icons") or meta.get("favicons")
    favicon = None
    if isinstance(icons, list) and icons:
        favicon = icons[0]
    elif isinstance(icons, str):
        favicon = icons

    return {
        "title": meta.get("title"),
        "description": (
            meta.get("description")
            or meta.get("og:description")
            or meta.get("twitter:description")
        ),
        "banner_image": (
            meta.get("image") or meta.get("og:image") or meta.get("twitter:image")
        ),
        "favicon": favicon
        or f"{urlparse(url).scheme}://{urlparse(url).netloc}/favicon.ico",
    }


class CrawlerEngine:
    def __init__(
        self,
        batch_size: int = 10,
        concurrency: int = 8,
    ):
        self.browser_cfg = BrowserConfig(
            headless=True,
            text_mode=True,
            light_mode=True,
            java_script_enabled=False,
        )

        self.batch_size = batch_size
        self.concurrency = concurrency

        self.crawler: Optional[AsyncWebCrawler] = None
        self.running = False

    async def start(self):
        if self.running:
            return

        self.crawler = AsyncWebCrawler(config=self.browser_cfg)
        await self.crawler.start()
        self.running = True

    async def stop(self):
        if self.crawler:
            await self.crawler.close()
        self.running = False

    async def crawl_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        if not self.running:
            await self.start()

        all_results = []
        start_all = time.time()

        for i in range(0, len(urls), self.batch_size):
            batch_urls = urls[i : i + self.batch_size]
            print(f"🚀 Batch {i // self.batch_size + 1} ({len(batch_urls)} URLs)")

            run_configs = [
                CrawlerRunConfig(
                    page_timeout=5000,  # 5s internal limit (we enforce 6s externally)
                    wait_for=None,
                    cache_mode=CacheMode.BYPASS,
                    semaphore_count=self.concurrency,
                    mean_delay=0.1,
                    max_range=0.3,
                )
                for _ in batch_urls
            ]

            try:
                # Hard Python-level timeout: cancel whole batch if >6s
                async with asyncio.timeout(6.0):
                    batch_results = await self.crawler.arun_many(
                        urls=batch_urls,
                        configs=run_configs,
                    )
            except asyncio.TimeoutError:
                print("⚠️ Batch timeout after 6s - skipping remaining in batch")
                # Mark remaining as timeout (approximate)
                for u in batch_urls:
                    all_results.append(
                        {
                            "url": u,
                            "status": "timeout",
                            "title": None,
                            "description": None,
                            "favicon": None,
                            "banner_image": None,
                            "markdown": None,
                            "crawling_time_sec": 6.0,
                            "error": "Hard timeout after 6 seconds",
                        }
                    )
                continue  # next batch

            for result in batch_results:
                meta = _normalize_metadata(result.metadata, result.url)

                status = "success" if result.success else "fail"
                if result.error_message and "timeout" in result.error_message.lower():
                    status = "timeout"

                desc = meta.get("description") or (
                    result.markdown[:300] if result.markdown else None
                )

                all_results.append(
                    {
                        "url": result.url,
                        "status": status,
                        "title": meta.get("title"),
                        "description": desc,
                        "favicon": meta.get("favicon"),
                        "banner_image": meta.get("banner_image"),
                        "markdown": result.markdown if result.success else None,
                        "crawling_time_sec": round(time.time() - start_all, 3),
                        "error": result.error_message if not result.success else None,
                    }
                )

        print(f"✅ Finished {len(urls)} URLs in {round(time.time() - start_all, 2)} s")
        return all_results


# Singleton (unchanged)
_engine: Optional[CrawlerEngine] = None


async def get_crawler_engine(
    batch_size: int = 10,
    concurrency: int = 8,
) -> CrawlerEngine:
    global _engine
    if _engine is None:
        _engine = CrawlerEngine(batch_size=batch_size, concurrency=concurrency)
        await _engine.start()
    return _engine


async def crawl_urls(
    urls: List[str],
    batch_size: int = 10,
    concurrency: int = 8,
) -> List[Dict[str, Any]]:
    engine = await get_crawler_engine(batch_size=batch_size, concurrency=concurrency)
    return await engine.crawl_batch(urls)
