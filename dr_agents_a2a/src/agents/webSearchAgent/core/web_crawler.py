import asyncio
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

# -------------------------------
# 🔧 Helpers to detect "empty" or JS-blocked content
# -------------------------------
EMPTY_PATTERNS = [
    r"(?i)enable javascript",
    r"(?i)javascript is disabled",
    r"(?i)turn on javascript",
    r"(?i)please wait while your request is being verified",
    r"(?i)loading.*please wait",
]


def _looks_empty_or_blocked(markdown: str | None) -> bool:
    if not markdown or len(markdown.strip()) < 400:
        return True
    for pat in EMPTY_PATTERNS:
        if re.search(pat, markdown):
            return True
    return False


# Metadata normalizer (unchanged)
def _normalize_metadata(meta: Optional[dict], url: str) -> Dict[str, Any]:
    if not meta:
        parsed = urlparse(url)
        return {
            "title": None,
            "description": None,
            "banner_image": None,
            "favicon": f"{parsed.scheme}://{parsed.netloc}/favicon.ico",
        }

    favicon = meta.get("favicon") or (
        meta.get("icons")[0]
        if isinstance(meta.get("icons"), list) and meta.get("icons")
        else None
    )

    return {
        "title": meta.get("title"),
        "description": meta.get("description")
        or meta.get("og:description")
        or meta.get("twitter:description"),
        "banner_image": meta.get("image")
        or meta.get("og:image")
        or meta.get("twitter:image"),
        "favicon": favicon
        or f"{urlparse(url).scheme}://{urlparse(url).netloc}/favicon.ico",
    }


# -------------------------------
# 🧠 CrawlerEngine – Fixed for latest Crawl4AI (JS on BrowserConfig only)
# -------------------------------
class CrawlerEngine:
    def __init__(self, batch_size: int = 10, max_concurrency: int = 10):
        # No-JS config (fast default for most search-result pages)
        self.nojs_browser_cfg = BrowserConfig(
            headless=True,
            text_mode=True,  # disables images → huge speed
            light_mode=True,
            java_script_enabled=False,  # ← here only!
        )

        # With-JS config (fallback when needed)
        self.js_browser_cfg = BrowserConfig(
            headless=True,
            text_mode=False,  # allow JS to render properly
            light_mode=False,
            java_script_enabled=True,
        )

        self.batch_size = batch_size
        self.max_concurrency = max_concurrency

        self.nojs_crawler: Optional[AsyncWebCrawler] = None
        self.js_crawler: Optional[AsyncWebCrawler] = None

        self.running = False

    async def start(self):
        if self.running:
            return

        self.nojs_crawler = AsyncWebCrawler(config=self.nojs_browser_cfg)
        self.js_crawler = AsyncWebCrawler(config=self.js_browser_cfg)

        await asyncio.gather(
            self.nojs_crawler.start(),
            self.js_crawler.start(),
        )
        self.running = True

    async def stop(self):
        if self.nojs_crawler:
            await self.nojs_crawler.close()
        if self.js_crawler:
            await self.js_crawler.close()
        self.running = False

    # -------------------------------
    # ⚡ Single URL adaptive crawl
    # -------------------------------
    async def _crawl_single(self, url: str) -> Dict[str, Any]:
        start_time = time.time()

        # Phase 1: Fast NO-JS attempt
        nojs_config = CrawlerRunConfig(
            page_timeout=3000,  # 3s hard
            wait_for=None,
            cache_mode=CacheMode.BYPASS,
        )

        result = await self.nojs_crawler.arun(url=url, config=nojs_config)

        final_result = result
        used_js = False

        # Phase 2: If empty/blocked → retry WITH JS
        if not result.success or _looks_empty_or_blocked(result.markdown):
            js_config = CrawlerRunConfig(
                page_timeout=5000,
                wait_for="networkidle",
                wait_timeout=4000,
                cache_mode=CacheMode.BYPASS,
            )
            result_js = await self.js_crawler.arun(url=url, config=js_config)

            if (
                result_js.success
                and result_js.markdown
                and len(result_js.markdown) > (len(result.markdown or "") + 200)
            ):
                final_result = result_js
                used_js = True

        status = "success" if final_result.success else "fail"
        if _looks_empty_or_blocked(final_result.markdown):
            status = "empty_or_blocked"

        meta = _normalize_metadata(final_result.metadata, url)

        desc = meta.get("description") or (
            final_result.markdown[:300] if final_result.markdown else None
        )

        return {
            "url": url,
            "status": status,
            "title": meta.get("title"),
            "description": desc,
            "favicon": meta.get("favicon"),
            "banner_image": meta.get("banner_image"),
            "markdown": final_result.markdown if final_result.success else None,
            "crawling_time_sec": round(time.time() - start_time, 3),
            "error": final_result.error_message if not final_result.success else None,
            "used_js": used_js,
        }

    async def crawl_batch(self, urls: List[str]) -> List[Dict[str, Any]]:
        if not self.running:
            await self.start()

        results = []
        start_all = time.time()

        for i in range(0, len(urls), self.batch_size):
            batch = urls[i : i + self.batch_size]
            print(f"🚀 Batch {i // self.batch_size + 1} ({len(batch)} URLs)")

            tasks = [self._crawl_single(u) for u in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in batch_results:
                if isinstance(res, Exception):
                    results.append(
                        {
                            "url": "unknown",
                            "status": "exception",
                            "error": str(res),
                            "crawling_time_sec": round(time.time() - start_all, 3),
                        }
                    )
                else:
                    results.append(res)

        print(f"✅ Done {len(urls)} URLs in {round(time.time() - start_all, 2)}s")
        return results


# Singleton + helper (your existing import points here)
_engine: Optional[CrawlerEngine] = None


async def get_crawler_engine(batch_size: int = 10) -> CrawlerEngine:
    global _engine
    if _engine is None:
        _engine = CrawlerEngine(batch_size=batch_size)
        await _engine.start()
    return _engine


async def crawl_urls(urls: List[str], batch_size: int = 10) -> List[Dict[str, Any]]:
    engine = await get_crawler_engine(batch_size)
    return await engine.crawl_batch(urls)
