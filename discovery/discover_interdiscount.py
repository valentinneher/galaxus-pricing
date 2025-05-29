# Scrape ALL pages from Interdiscount's search (pages are 0-indexed!), save fields to CSV.
# Now: prints each page being checked!

import asyncio
import aiohttp
import async_timeout
import csv
from typing import List

SEARCH_API_URL = (
    "https://www.interdiscount.ch/idocc/occ/id/products/search?lang=de&query=apple%3Arelevance%3Abrand%3AAPPLE&pageSize=24&page={page}"
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
    codes = []
    async with aiohttp.ClientSession() as session:
        # Fetch first page to get total count and codes
        page = 0
        print(f"Checking page {page + 1} ...")
        url = SEARCH_API_URL.format(page=page)
        page_json = await fetch_json(session, url)
        products = page_json['products']
        pagination = page_json.get('pagination', {})
        total = pagination.get('totalNumberOfResults', len(products))
        number_of_pages = pagination.get('numberOfPages', 1)
        codes += [p.get('code') for p in products if 'code' in p]
        print(f"Found {total} products, spanning {number_of_pages} pages...")
        # Pages are 0-indexed!
        for p in range(1, number_of_pages):
            print(f"Checking page {p + 1} ...")
            url = SEARCH_API_URL.format(page=p)
            page_json = await fetch_json(session, url)
            codes += [p.get('code') for p in page_json['products'] if 'code' in p]
    print(f"Total product codes collected: {len(codes)}")
    return codes

async def fetch_product_details(session: aiohttp.ClientSession, codes: List[str]):
    details = []
    for i in range(0, len(codes), DETAIL_BATCH_SIZE):
        batch = codes[i:i + DETAIL_BATCH_SIZE]
        ids_str = ",".join(batch)
        url = DETAILS_API_URL.format(ids=ids_str)
        batch_details = await fetch_json(session, url)
        if isinstance(batch_details, list):
            details.extend(batch_details)
    return details

async def main():
    codes = await discover_product_codes()
    async with aiohttp.ClientSession() as session:
        details = await fetch_product_details(session, codes)
        parsed = [build_product_dict(p) for p in details]
        with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in parsed:
                writer.writerow(row)
        print(f"Saved {OUT_CSV} (rows ≈ {len(parsed)})")

if __name__ == "__main__":
    asyncio.run(main())
