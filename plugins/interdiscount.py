import asyncio
import time
from typing import AsyncGenerator, List, Dict

# For the real scraper you’ll need aiohttp, cssselect, etc.
# For now we emit dummy prices so the pipeline works end-to-end.


async def fetch_batch(
    session,  # aiohttp.ClientSession (ignored in the stub)
    batch: List[Dict],
) -> AsyncGenerator[Dict, None]:
    """
    Yield one fake price record per SKU in the batch.
    Replace this with real HTTP scraping when ready.
    """
    now = int(time.time())
    for item in batch:
        await asyncio.sleep(0)               # keep function async-friendly
        yield {
            "shop": "interdiscount",
            "code": item["code"],
            "ean": item.get("ean"),
            "price": 999,                    # placeholder price
            "ts": now,
        }