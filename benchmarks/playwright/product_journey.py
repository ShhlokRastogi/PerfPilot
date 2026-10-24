import time
import json
import asyncio
from typing import Dict, Any

async def simulate_browser_journey(target_url: str) -> Dict[str, Any]:
    """
    Simulates a functional user browser journey measuring TTFB and transaction latency.
    """
    import httpx
    start_time = time.perf_counter()
    async with httpx.AsyncClient() as client:
        # Step 1: Health / Initial Navigation
        t0 = time.perf_counter()
        resp_health = await client.get("http://127.0.0.1:8001/health", timeout=5.0)
        ttfb_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        
        # Step 2: Product Catalog View
        t1 = time.perf_counter()
        resp_products = await client.get(target_url, timeout=10.0)
        catalog_latency_ms = round((time.perf_counter() - t1) * 1000.0, 2)
        
        # Step 3: Product Detail View
        t2 = time.perf_counter()
        resp_detail = await client.get("http://127.0.0.1:8001/api/products/1", timeout=5.0)
        detail_latency_ms = round((time.perf_counter() - t2) * 1000.0, 2)

    total_journey_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
    success = (
        resp_health.status_code == 200 and
        resp_products.status_code == 200 and
        resp_detail.status_code == 200
    )

    return {
        "success": success,
        "ttfb_ms": ttfb_ms,
        "catalog_latency_ms": catalog_latency_ms,
        "detail_latency_ms": detail_latency_ms,
        "total_journey_duration_ms": total_journey_ms,
        "steps_completed": 3,
        "errors": [] if success else ["One or more journey endpoints failed"]
    }

if __name__ == "__main__":
    result = asyncio.run(simulate_browser_journey("http://127.0.0.1:8001/api/products"))
    print(json.dumps(result, indent=2))
