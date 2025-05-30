import asyncio
import aiohttp
import async_timeout
import csv
from typing import List

SEARCH_API_URL = (
    "https://www.interdiscount.ch/idocc/occ/id/products/search?lang=de&query=apple%3Arelevance%3Abrand%3AAPPLE&pageSize=24&currentPage={page}"
)
DETAILS_API_URL = (
    "https://www.interdiscount.ch/api/v1/products?ids={ids}&locale=de&fieldSet=DEFAULT"
)
OUT_CSV = "apple_interdiscount.csv"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Referer": "https://www.interdiscount.ch/de/search?search=apple&brand=APPLE",
    "DNT": "1",
}
RATE_LIMIT = 1
MAX_RETRIES = 4
PAGE_SIZE = 24
DETAIL_BATCH_SIZE = 20
FIELDNAMES = ["shop", "code", "ean", "url", "name", "price", "selector"]

def build_product_dict(product):
    return {
        "shop": "interdiscount",
        "code": product.get("code"),
        "ean": product.get("ean"),
        "url": f"https://www.interdiscount.ch{product.get('url', '')}",
        "name": product.get("name"),
        "price": product.get("finalPrice", {}).get("value"),
        "selector": 'script[type="application/ld+json"]',
    }

async def fetch_json(session: aiohttp.ClientSession, url: str):
    delay = 1 / RATE_LIMIT
    for attempt in range(MAX_RETRIES):
        if attempt:
            await asyncio.sleep(delay * 2 ** attempt)
        else:
            await asyncio.sleep(delay)
        try:
            async with async_timeout.timeout(20):
                async with session.get(url, headers=HEADERS) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == MAX_RETRIES - 1:
                raise

async def discover_product_codes():
    codes = set()  # Use set to avoid duplicates
    async with aiohttp.ClientSession() as session:
        page = 1
        print(f"Checking page {page} ...")
        url = SEARCH_API_URL.format(page=page)
        page_json = await fetch_json(session, url)
        products = page_json['products']
        pagination = page_json.get('pagination', {})
        total = pagination.get('totalNumberOfResults', len(products))
        number_of_pages = pagination.get('numberOfPages', 1)
        for p in products:
            if 'code' in p:
                codes.add(p['code'])
        print(f"Found {total} products, spanning {number_of_pages} pages...")
        for p in range(2, number_of_pages + 1):  # API is 1-based and inclusive
            print(f"Checking page {p} ...")
            url = SEARCH_API_URL.format(page=p)
            page_json = await fetch_json(session, url)
            products = page_json.get('products', [])
            if not products:
                print(f"Page {p} is empty!")
            else:
                print(f"Page {p} returned {len(products)} products. Codes: {[prod.get('code') for prod in products]}")
            for prod in products:
                if 'code' in prod:
                    codes.add(prod['code'])
    print(f"Total unique product codes collected: {len(codes)}")
    return list(codes)

async def fetch_product_details(session: aiohttp.ClientSession, codes: List[str]):
    details = []
    seen_codes = set()
    for i in range(0, len(codes), DETAIL_BATCH_SIZE):
        batch = codes[i:i + DETAIL_BATCH_SIZE]
        ids_str = ",".join(batch)
        url = DETAILS_API_URL.format(ids=ids_str)
        batch_details = await fetch_json(session, url)
        if isinstance(batch_details, list):
            for product in batch_details:
                code = product.get("code")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    details.append(product)
    return details

async def main():
    codes = await discover_product_codes()
    async with aiohttp.ClientSession() as session:
        details = await fetch_product_details(session, codes)
        # Deduplicate by 'code' just in case
        deduped = {}
        for p in details:
            code = p.get('code')
            if code:
                deduped[code] = build_product_dict(p)
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in deduped.values():
                writer.writerow(row)
        print(f"Saved {OUT_CSV} (unique rows ≈ {len(deduped)})")

# This makes it compatible with environments that already have an event loop (e.g., Jupyter, some IDEs)
if __name__ == "__main__":
    try:
        import sys
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In a running event loop (Jupyter, etc), use ensure_future
            task = loop.create_task(main())
            # If in a script, optionally wait for the task to finish:
            # await task
        else:
            loop.run_until_complete(main())
    except RuntimeError:
        # Fallback: If no event loop, use asyncio.run
        asyncio.run(main())
