# Debug version: Print full JSON from the first page to see all fields and pagination logic

import asyncio
import aiohttp
import async_timeout
import math

SEARCH_API_URL = (
    "https://www.interdiscount.ch/idocc/occ/id/products/search?lang=de&query=apple%3Arelevance%3Abrand%3AAPPLE&pageSize=24&page={page}"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.interdiscount.ch/de/search?search=apple&brand=APPLE",
    "DNT": "1",
}

async def fetch_json(session: aiohttp.ClientSession, url: str):
    async with async_timeout.timeout(20):
        async with session.get(url, headers=HEADERS) as resp:
            resp.raise_for_status()
            return await resp.json()

async def main():
    async with aiohttp.ClientSession() as session:
        url = SEARCH_API_URL.format(page=1)
        page_json = await fetch_json(session, url)
        print("\n--- FULL RAW JSON ---\n")
        import json
        print(json.dumps(page_json, indent=2, ensure_ascii=False))
        print("\n--- END JSON ---\n")
        if isinstance(page_json, dict):
            print(f"top-level keys: {list(page_json.keys())}")
            if 'pagination' in page_json:
                print(f"pagination: {page_json['pagination']}")
            if 'products' in page_json:
                print(f"len(products): {len(page_json['products'])}")
        elif isinstance(page_json, list):
            print(f"list of {len(page_json)} items")

if __name__ == "__main__":
    asyncio.run(main())
