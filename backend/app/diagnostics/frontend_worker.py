import time
import httpx
import re
from typing import Dict, Any, List
from backend.app.diagnostics.base import DiagnosticWorker
from backend.app.evidence.schema import EvidenceRecord

class FrontendDiagnosticWorker(DiagnosticWorker):
    """
    Frontend Diagnostic Agent:
    Uses Playwright headless browser (when available) or web asset waterfall
    to measure TTFB, DOMContentLoaded, LCP, and render-blocking scripts for web targets.
    """
    @property
    def name(self) -> str:
        return "FrontendDiagnosticWorker"

    @property
    def category(self) -> str:
        return "frontend"

    async def investigate(
        self,
        run_id: str,
        target_url: str,
        repo_path: str,
        baseline_metrics: Dict[str, Any]
    ) -> List[EvidenceRecord]:
        records: List[EvidenceRecord] = []

        # Attempt Playwright headless browser measurement
        playwright_available = False
        try:
            from playwright.async_api import async_playwright
            playwright_available = True
        except ImportError:
            playwright_available = False

        if playwright_available:
            try:
                from playwright.async_api import async_playwright
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    t0 = time.perf_counter()
                    response = await page.goto(target_url, wait_until="networkidle", timeout=15000)
                    total_nav_ms = (time.perf_counter() - t0) * 1000.0

                    timing = await page.evaluate("() => JSON.stringify(window.performance.timing)")
                    lcp = await page.evaluate("""() => {
                        return new Promise((resolve) => {
                            new PerformanceObserver((entryList) => {
                                const entries = entryList.getEntries();
                                const lastEntry = entries[entries.length - 1];
                                resolve(lastEntry ? lastEntry.startTime : 0);
                            }).observe({type: 'largest-contentful-paint', buffered: true});
                            setTimeout(() => resolve(0), 1000);
                        });
                    }""")
                    await browser.close()

                    records.append(
                        EvidenceRecord(
                            run_id=run_id,
                            category=self.category,
                            observation=f"Playwright browser trace measured navigation completion in {total_nav_ms:.1f}ms with Largest Contentful Paint (LCP) of {float(lcp):.1f}ms.",
                            measured_values={
                                "navigation_ms": round(total_nav_ms, 2),
                                "lcp_ms": round(float(lcp), 2),
                                "http_status": response.status if response else 200
                            },
                            unit="ms",
                            source_type="playwright",
                            collection_method="playwright_headless_chromium",
                            provenance="real_browser_render",
                            limitations="Single-page load in synthetic headless environment; real user device network variations not included."
                        )
                    )
                    return records
            except Exception as e:
                # Fallback to HTTP web asset inspection
                records.append(
                    EvidenceRecord(
                        run_id=run_id,
                        category=self.category,
                        observation=f"Playwright browser execution encountered: {str(e)}. Falling back to static web asset analysis.",
                        measured_values={"error": str(e)},
                        source_type="http_metric",
                        limitations="Headless browser execution was not possible; static asset audit performed."
                    )
                )

        # Fallback: Static web asset inspection over HTTP
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                t0 = time.perf_counter()
                resp = await client.get(target_url)
                ttfb_ms = (time.perf_counter() - t0) * 1000.0
                body = resp.text

                # Count synchronous script tags and stylesheets
                scripts = re.findall(r"<script[^>]*src=[\"']([^\"']+)[\"'][^>]*>", body, re.IGNORECASE)
                sync_scripts = [s for s in scripts if "async" not in s and "defer" not in s]
                stylesheets = re.findall(r"<link[^>]*rel=[\"']stylesheet[\"'][^>]*>", body, re.IGNORECASE)

                records.append(
                    EvidenceRecord(
                        run_id=run_id,
                        category=self.category,
                        observation=(
                            f"Web target rendered HTML document ({len(body)} bytes) with TTFB of {ttfb_ms:.1f}ms. "
                            f"Detected {len(sync_scripts)} synchronous render-blocking script tag(s) and {len(stylesheets)} external stylesheet(s)."
                        ),
                        measured_values={
                            "ttfb_ms": round(ttfb_ms, 2),
                            "html_bytes": len(body),
                            "sync_script_count": len(sync_scripts),
                            "stylesheet_count": len(stylesheets)
                        },
                        unit="ms",
                        source_type="http_metric",
                        collection_method="http_document_parser",
                        provenance="http_client_inspection",
                        limitations="Playwright was not available; DOM rendering, CSS layout times, and JS execution times could not be measured directly."
                    )
                )
        except Exception as e:
            records.append(
                EvidenceRecord(
                    run_id=run_id,
                    category=self.category,
                    observation=f"Failed to inspect web target document: {str(e)}",
                    measured_values={"error": str(e)},
                    source_type="http_metric",
                    limitations="Web endpoint was unreachable during frontend diagnostic."
                )
            )

        return records
