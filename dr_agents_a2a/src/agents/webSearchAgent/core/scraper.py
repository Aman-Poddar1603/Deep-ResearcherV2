# test_crawler.py
# Run this file separately to test your crawler
# Make sure your project structure allows the import below

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

# Your crawler imports (adjust path if needed)
from src.agents.webSearchAgent.core.web_crawler import (
    crawl_urls,
    get_crawler_engine,
)

# ────────────────────────────────────────────────
# 50 Test URLs — mix of travel, recipes, local Ranchi/Jharkhand, general
# ────────────────────────────────────────────────
TEST_URLS: List[str] = [
    # Your original 10 (travel/flight heavy — expect many blocked/empty)
    "https://www.baliholidaysecrets.com/flights-from-india-to-bali/",
    "https://www.kayak.co.in/flight-routes/India-IN0/Bali-IDBA",
    "https://www.momondo.in/flights/india/bali",
    "https://in.trip.com/flights/to-bali/airfares-dps/",
    "https://www.wego.co.in/flights/in/dps/cheapest-flights-from-india-to-bali-1906",
    "https://www.airindia.com/in/en/book/exclusive-deals/india-bali-flight-sale.html",
    "https://www.tripadvisor.in/Flights-g294226-Bali-Cheap_Discount_Airfares.html",
    "https://www.google.com/travel/flights/flights-to-bali.html?gl=IN&hl=en",
    "https://www.makemytrip.com/international-flights/india-denpasar_bali-cheap-airtickets.html",
    "https://www.skyscanner.co.in/flights/flights-to-region/44292244/cheap-flights-to-bali.html",
    # Travel / Bali / India guides — lighter pages
    "https://www.baliholidaysecrets.com/flights-from-india-to-bali/",
    "https://www.lonelyplanet.com/indonesia/bali",
    "https://www.tripoto.com/india/trips/best-places-to-visit-in-bali-for-indians",
    "https://www.holidify.com/places/bali/sightseeing-and-things-to-do.html",
    # Beginner Indian recipes (mostly static — should be fast & successful)
    "https://www.allrecipes.com/gallery/best-indian-recipes-for-beginning-cooks",
    "https://www.bbcgoodfood.com/recipes/collection/indian-recipes",
    "https://www.foodnetwork.com/recipes/photos/indian-recipes",
    "https://www.allrecipes.com/recipes/233/world-cuisine/asian/indian/",
    "https://www.bbcgoodfood.com/recipes/kitchari",
    "https://www.allrecipes.com/recipe/23600/indian-butter-chicken/",
    "https://www.bbcgoodfood.com/recipes/healthy-tikka-masala",
    "https://www.allrecipes.com/recipe/141939/easy-indian-butter-chicken/",
    # Ranchi / Jharkhand tourist places (local relevance — mix of light & medium)
    "https://www.tripadvisor.com/Attractions-g662320-Activities-Ranchi_Ranchi_District_Jharkhand.html",
    "https://www.holidify.com/places/ranchi/sightseeing-and-things-to-do.html",
    "https://www.makemytrip.com/tripideas/places/ranchi",
    "https://www.travelladda.com/best-places-to-visit-in-ranchi",
    "https://us.trip.com/travel-guide/destination/ranchi-2131241",
    "https://www.treebo.com/blog/12-places-to-visit-in-ranchi",
    "https://www.tripclap.com/places/ranchi/places-to-visit",
    # Some Ranchi/Jharkhand news or recent pages (March 2026 context)
    "https://www.uniindia.com/ranchi-on-high-alert-a-jharkhand-on-high-alert-ahead-of-president-murmu-s-3-day-visit/east/news/3687573.html",
    # If you have a local news site you like, add more here
    # General / diverse test cases (Wikipedia, blogs, etc.)
    "https://en.wikipedia.org/wiki/Ranchi",
    "https://en.wikipedia.org/wiki/Bali",
    "https://en.wikipedia.org/wiki/Indian_cuisine",
    "https://www.bbc.com/news/topics/cvenzmgyg4rt/india",
    "https://www.thehindu.com/news/national/jharkhand/",
    "https://timesofindia.indiatimes.com/city/ranchi",
]


async def run_test():
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting crawler test with {len(TEST_URLS)} URLs..."
    )

    # Optional: warm up engine first (helps avoid cold-start lag)
    engine = await get_crawler_engine(batch_size=10)
    print("Engine warmed up.")

    # Run the batch crawl
    results: List[Dict[str, Any]] = await crawl_urls(TEST_URLS, batch_size=10)

    # Print summary stats
    success = sum(1 for r in results if r.get("status") == "success")
    blocked_empty = sum(
        1 for r in results if r.get("status") in ["empty_or_blocked", "blocked"]
    )
    fail = sum(1 for r in results if r.get("status") == "fail")
    total_time = max(r.get("crawling_time_sec", 0) for r in results)  # rough batch time

    print("\n" + "=" * 60)
    print(f"RESULTS SUMMARY ({len(results)} URLs)")
    print(f"Success       : {success}")
    print(f"Blocked/Empty : {blocked_empty}")
    print(f"Fail/Timeout  : {fail}")
    print(f"Rough total time: ~{total_time:.1f} sec (parallel batches)")
    print("=" * 60 + "\n")

    # Print short report for each (you can save to file too)
    for r in results:
        status_emoji = (
            "✅"
            if r["status"] == "success"
            else "⚠️"
            if r["status"] in ["empty_or_blocked", "fail"]
            else "❌"
        )
        js_note = " (used JS)" if r.get("used_js") else ""
        print(
            f"{status_emoji} {r['status'].upper():<12} | {r['crawling_time_sec']:.2f}s | {r['url'][:80]}{'...' if len(r['url']) > 80 else ''}{js_note}"
        )

    # Optional: save full results to JSON for inspection
    with open("crawler_test_results_2026.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("\nFull results saved to: crawler_test_results_2026.json")


if __name__ == "__main__":
    asyncio.run(run_test())
