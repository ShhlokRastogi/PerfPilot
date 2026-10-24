import httpx
import time
from typing import Dict, Any, List
from backend.app.diagnostics.base import DiagnosticWorker
from backend.app.evidence.schema import EvidenceRecord

class BackendDiagnosticWorker(DiagnosticWorker):
    """
    Backend Diagnostic Agent:
    Investigates backend API latency breakdowns, OpenTelemetry trace spans,
    HTTP timing components, and server error rates.
    """
    @property
    def name(self) -> str:
        return "BackendDiagnosticWorker"

    @property
    def category(self) -> str:
        return "backend"

    async def investigate(
        self,
        run_id: str,
        target_url: str,
        repo_path: str,
        baseline_metrics: Dict[str, Any]
    ) -> List[EvidenceRecord]:
        records: List[EvidenceRecord] = []
        p95_ms = float(baseline_metrics.get("p95_latency_ms", 0.0))
        error_rate = float(baseline_metrics.get("error_rate_pct", 0.0))
        rps = float(baseline_metrics.get("throughput_rps", 0.0))

        # Record empirical baseline metric as primary evidence
        records.append(
            EvidenceRecord(
                run_id=run_id,
                category=self.category,
                observation=f"Benchmark load test measured p95 latency of {p95_ms:.1f}ms and throughput of {rps:.1f} req/s with {error_rate:.2f}% error rate under concurrency.",
                measured_values={
                    "p50_latency_ms": baseline_metrics.get("p50_latency_ms"),
                    "p90_latency_ms": baseline_metrics.get("p90_latency_ms"),
                    "p95_latency_ms": p95_ms,
                    "p99_latency_ms": baseline_metrics.get("p99_latency_ms"),
                    "throughput_rps": rps,
                    "error_rate_pct": error_rate,
                    "total_requests": baseline_metrics.get("total_requests")
                },
                unit="ms",
                source_type="http_metric",
                collection_method="k6_workload_runner",
                provenance="deterministic_load_test"
            )
        )

        # Inspect target endpoint headers for OpenTelemetry or distributed trace context
        trace_id = None
        span_id = None
        has_otel_headers = False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                t0 = time.perf_counter()
                resp = await client.get(target_url)
                t_elapsed_ms = (time.perf_counter() - t0) * 1000.0

                headers = {k.lower(): v for k, v in resp.headers.items()}
                # Check for standard W3C Trace Context (traceparent: 00-{trace_id}-{span_id}-{trace_flags})
                if "traceparent" in headers:
                    parts = headers["traceparent"].split("-")
                    if len(parts) >= 3:
                        trace_id = parts[1]
                        span_id = parts[2]
                        has_otel_headers = True
                elif "x-trace-id" in headers:
                    trace_id = headers["x-trace-id"]
                    has_otel_headers = True

                records.append(
                    EvidenceRecord(
                        run_id=run_id,
                        category=self.category,
                        observation=(
                            f"Single-probe HTTP GET to target returned HTTP status {resp.status_code} in {t_elapsed_ms:.1f}ms. "
                            f"{'W3C trace context header identified.' if has_otel_headers else 'No OpenTelemetry traceparent header exposed by target.'}"
                        ),
                        measured_values={
                            "single_request_latency_ms": round(t_elapsed_ms, 2),
                            "http_status": resp.status_code,
                            "content_length_bytes": len(resp.content),
                            "has_otel_headers": has_otel_headers
                        },
                        unit="ms",
                        source_type="opentelemetry" if has_otel_headers else "http_metric",
                        trace_id=trace_id,
                        span_id=span_id,
                        collection_method="http_probe",
                        limitations="Black-box external probe; does not prove exact CPU line hotspots unless corroborated by AST or profiling."
                    )
                )
        except Exception as e:
            records.append(
                EvidenceRecord(
                    run_id=run_id,
                    category=self.category,
                    observation=f"Direct HTTP diagnostic probe encountered connection event: {str(e)}",
                    measured_values={"error": str(e)},
                    source_type="http_metric",
                    provenance="diagnostic_probe",
                    limitations="Endpoint was temporarily unreachable during single-probe diagnostic."
                )
            )

        return records
