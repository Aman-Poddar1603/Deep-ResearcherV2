# test_crawler.py
# Run this file separately to test your crawler
# Make sure your project structure allows the import below

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

# Your crawler imports (adjust path if needed)
from .web_crawler import (
    crawl_urls,
    get_crawler_engine,
)

# ────────────────────────────────────────────────
# 50 Test URLs — mix of travel, recipes, local Ranchi/Jharkhand, general
# ────────────────────────────────────────────────
TEST_URLS = [
    # Travel / destinations (new ones)
    "https://www.thrillophilia.com/places-to-visit-in-ranchi",
    "https://www.fabhotels.com/blog/places-to-visit-in-ranchi/",
    "https://www.nativeplanet.com/ranchi/attractions/",
    "https://www.jharkhandtourism.gov.in/destinations/ranchi",
    "https://www.lonelyplanet.com/india/jharkhand/ranchi",
    "https://www.tripoto.com/jharkhand/trips/best-places-to-visit-in-ranchi",
    "https://www.makemytrip.com/tripideas/places-to-visit-in-goa",
    "https://www.holidify.com/places/goa/sightseeing-and-things-to-do.html",
    "https://www.thrillophilia.com/places-to-visit-in-kerala",
    "https://www.fabhotels.com/blog/places-to-visit-in-kerala/",
    # Recipes (fresh Indian + some fusion)
    "https://www.swasthi.com/chicken-biryani-recipe",
    "https://www.indianhealthyrecipes.com/paneer-butter-masala-recipe/",
    "https://www.vegrecipesofindia.com/pav-bhaji-recipe/",
    "https://www.tarladalal.com/recipes-for-indian-vegetarian-209",
    "https://www.sanjeevkapoor.com/recipe/Aloo-Paratha-Indian-Bread-with-Potato-Filling.html",
    "https://www.archanaskitchen.com/recipes/indian-breakfast-recipes",
    "https://www.vegrecipesofindia.com/dal-makhani-recipe/",
    "https://www.indianhealthyrecipes.com/rasmalai-recipe/",
    "https://www.swasthi.com/rajma-recipe-rajma-masala-recipe/",
    "https://www.tarladalal.com/recipes-for-south-indian-vegetarian-210",
    # Ranchi / Jharkhand local (new pages)
    "https://ranchi.nic.in/tourist-places/",
    "https://www.jharkhandtourism.gov.in/destinations/jamshedpur",
    "https://www.tripadvisor.in/Attractions-g662320-Activities-c47-t26-Ranchi_Ranchi_District_Jharkhand.html",
    "https://www.holidify.com/places/ranchi/jagannath-temple-sightseeing-125612.html",
    "https://ranchi.nic.in/places-of-interest/",
    "https://www.nativeplanet.com/ranchi/hundru-falls/",
    "https://www.jharkhandtourism.gov.in/destinations/dassam-falls",
    "https://www.tripoto.com/ranchi/trips/weekend-getaways-near-ranchi",
    "https://www.fabhotels.com/blog/best-places-to-visit-in-jharkhand/",
    "https://ranchi.nic.in/paras-nath-hill/",
    # General / diverse / news / articles
    "https://www.thehindu.com/news/national/other-states/jharkhand/",
    "https://indianexpress.com/section/india/jharkhand/",
    "https://www.prabhatkhabar.com/state/jharkhand/ranchi",
    "https://en.wikipedia.org/wiki/Jharkhand",
    "https://en.wikipedia.org/wiki/Ranchi_district",
    "https://www.bbc.com/news/world-asia-india-12345678",  # example, replace if dead
    "https://www.ndtv.com/india-news/jharkhand-news",
    "https://www.downtoearth.org.in/news/agriculture/jharkhand-farmers-struggle-with-drought-2025",
    "https://www.youthkiawaaz.com/tag/jharkhand/",
    "https://scroll.in/article/1067890/how-jharkhand-is-dealing-with-its-water-crisis",
    # Bonus: some e-commerce/product pages (test another type)
    "https://www.flipkart.com/apple-iphone-15-black-128-gb/p/itm6ac6485515ae4",
    "https://www.amazon.in/Samsung-Galaxy-Ultra-Storage-Without/dp/B0CX59H5W6",
    "https://www.myntra.com/men-tshirts/roadster/roadster-men-black-solid-polo-collar-t-shirt/1234567/buy",
    "https://www.ajio.com/peter-england-men-slim-fit-formal-shirt/p/460123456789",
]

print(f"New test set ready: {len(TEST_URLS)} URLs")


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
