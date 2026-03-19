import asyncio
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

BASE_DIR = Path(__file__).resolve().parent


class SearXNGClient:
    def __init__(
        self,
        base_url="http://localhost:8080",
        max_connections=50,
        max_concurrent_requests=5,  # 🔥 control aggression
    ):
        self.base_url = base_url.rstrip("/")

        # 🔥 concurrency limiter (ANTI-DDOS MODE)
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

        # 🔄 user-agent rotation
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
        ]

        # ⚡ connection pooling
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=10,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=20,
            ),
        )

        # 🧠 dedicated loop
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

    async def _search_async(self, query: str) -> Optional[Dict[str, Any]]:
        async with self._semaphore:  # 🚦 rate limiting
            headers = {
                "User-Agent": random.choice(self._user_agents),
                "Accept": "application/json",
            }

            retries = 2

            for attempt in range(retries + 1):
                try:
                    response = await self._client.get(
                        "/search",
                        params={"q": query, "format": "json"},
                        headers=headers,
                    )

                    response.raise_for_status()
                    return response.json()

                except Exception as e:
                    if attempt < retries:
                        await asyncio.sleep(0.5 * (attempt + 1))  # ⏳ backoff
                    else:
                        print(f"[ERROR] {query} -> {e}")
                        return None

    def search(self, query: str) -> Optional[Dict[str, Any]]:
        """Same usage (sync)"""
        return self._loop.run_until_complete(self._search_async(query))

    def search_parallel(self, queries: List[str]):
        """Parallel execution (controlled)"""

        async def runner():
            tasks = [self._search_async(q) for q in queries]
            return await asyncio.gather(*tasks)

        return self._loop.run_until_complete(runner())

    async def search_fire_and_forget(self, query: str):
        """🔥 non-blocking trigger"""
        asyncio.create_task(self._search_async(query))

    async def close(self):
        await self._client.aclose()
