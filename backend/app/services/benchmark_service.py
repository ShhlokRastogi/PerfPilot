import os
import json
import asyncio
import time
import subprocess
import statistics
from typing import Dict, Any, Optional, List
import httpx
from backend.app.core.config import settings

K6_LOCAL_BIN = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../benchmarks/bin/k6.exe"))
K6_SCRIPT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../benchmarks/k6/dynamic_workload_runner.js"))

class BenchmarkExecutionError(Exception):
    pass

class BenchmarkService:
    @staticmethod
    def find_k6_binary() -> Optional[str]:
        if os.path.exists(K6_LOCAL_BIN):
            return K6_LOCAL_BIN
        # Check PATH
        import shutil
        path_bin = shutil.which("k6")
        if path_bin:
            return path_bin
        return None

    @classmethod
    async def run_benchmark(
        cls,
        run_id: str,
        phase: str,
        target_url: str,
        workload_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes benchmark workload against target_url using k6 if available,
        or high-precision async HTTP concurrent load runner.
        """
        vus = int(workload_config.get("vus", 10))
        duration_sec = int(workload_config.get("duration_sec", 8))
        
        # Ensure artifacts directory exists
        run_artifacts_dir = os.path.join(settings.ARTIFACTS_DIR, run_id)
        os.makedirs(run_artifacts_dir, exist_ok=True)
        summary_file = os.path.join(run_artifacts_dir, f"{phase}_k6_summary.json")

        k6_bin = cls.find_k6_binary()
        if k6_bin and os.path.exists(K6_SCRIPT_PATH):
            try:
                metrics = await cls._run_k6(
                    k6_bin=k6_bin,
                    target_url=target_url,
                    vus=vus,
                    duration_sec=duration_sec,
                    summary_file=summary_file,
                    personas=workload_config.get("personas")
                )
                metrics["phase"] = phase
                metrics["run_id"] = run_id
                return metrics
            except Exception as e:
                # If k6 encounters an execution error, log and fallback to async runner
                pass

        # Native Async Concurrent Benchmark Engine
        metrics = await cls._run_async_bench(
            target_url=target_url,
            concurrency=vus,
            duration_sec=duration_sec
        )
        metrics["phase"] = phase
        metrics["run_id"] = run_id
        
        # Save artifact
        with open(summary_file, "w") as f:
            json.dump(metrics, f, indent=2)

        return metrics

    @classmethod
    async def _run_k6(
        cls,
        k6_bin: str,
        target_url: str,
        vus: int,
        duration_sec: int,
        summary_file: str,
        personas: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        env = os.environ.copy()
        env["TARGET_URL"] = target_url
        env["VUS"] = str(vus)
        env["DURATION_SEC"] = str(duration_sec)
        if personas:
            env["PERSONAS_JSON"] = json.dumps(personas)

        cmd = [
            k6_bin,
            "run",
            "--summary-export",
            summary_file,
            K6_SCRIPT_PATH
        ]

        # Run k6 process asynchronously
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=duration_sec + 30)
        except asyncio.TimeoutError:
            proc.kill()
            raise BenchmarkExecutionError("k6 benchmark timed out")

        if proc.returncode != 0 and not os.path.exists(summary_file):
            raise BenchmarkExecutionError(f"k6 execution failed: {stderr.decode()}")

        with open(summary_file, "r") as f:
            data = json.load(f)

        metrics = data.get("metrics", {})
        dur_expected = metrics.get("http_req_duration{expected_response:true}")
        dur_raw = dur_expected if (dur_expected and dur_expected.get("count", 1) > 0) else metrics.get("http_req_duration", {})
        dur = dur_raw.get("values") if isinstance(dur_raw.get("values"), dict) else dur_raw

        reqs_raw = metrics.get("http_reqs", {})
        reqs = reqs_raw.get("values") if isinstance(reqs_raw.get("values"), dict) else reqs_raw

        failed_raw = metrics.get("http_req_failed", {})
        failed = failed_raw.get("values") if isinstance(failed_raw.get("values"), dict) else failed_raw

        return {
            "p50_latency_ms": round(dur.get("med", dur.get("p(50)", 0.0)), 2),
            "p90_latency_ms": round(dur.get("p(90)", 0.0), 2),
            "p95_latency_ms": round(dur.get("p(95)", 0.0), 2),
            "p99_latency_ms": round(dur.get("p(99)", 0.0), 2),
            "avg_latency_ms": round(dur.get("avg", 0.0), 2),
            "min_latency_ms": round(dur.get("min", 0.0), 2),
            "max_latency_ms": round(dur.get("max", 0.0), 2),
            "throughput_rps": round(reqs.get("rate", 0.0), 2),
            "total_requests": int(reqs.get("count", 0)),
            "failed_requests": int(failed.get("passes", 0)),
            "error_rate_pct": round(failed.get("rate", 0.0) * 100, 2),
            "duration_sec": float(duration_sec),
            "raw_data": data
        }

    @classmethod
    async def _run_async_bench(
        cls,
        target_url: str,
        concurrency: int,
        duration_sec: int
    ) -> Dict[str, Any]:
        """
        High-precision asynchronous concurrent HTTP benchmark runner.
        Executes bounded concurrent requests and records individual latencies.
        """
        latencies: list[float] = []
        failed_count = 0
        total_count = 0
        start_time = time.time()
        end_time = start_time + duration_sec

        async def worker(client: httpx.AsyncClient):
            nonlocal failed_count, total_count
            while time.time() < end_time:
                req_start = time.perf_counter()
                try:
                    resp = await client.get(target_url, timeout=10.0)
                    req_duration = (time.perf_counter() - req_start) * 1000.0
                    latencies.append(req_duration)
                    total_count += 1
                    if resp.status_code >= 400:
                        failed_count += 1
                except Exception:
                    req_duration = (time.perf_counter() - req_start) * 1000.0
                    latencies.append(req_duration)
                    total_count += 1
                    failed_count += 1
                await asyncio.sleep(0.02) # throttle slightly to mimic user think time

        limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency)
        async with httpx.AsyncClient(limits=limits) as client:
            tasks = [asyncio.create_task(worker(client)) for _ in range(concurrency)]
            await asyncio.gather(*tasks)

        actual_duration = time.time() - start_time
        if not latencies:
            return {
                "p50_latency_ms": 0.0,
                "p90_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "throughput_rps": 0.0,
                "total_requests": 0,
                "failed_requests": 0,
                "error_rate_pct": 0.0,
                "duration_sec": actual_duration,
                "raw_data": {}
            }

        latencies.sort()
        n = len(latencies)
        def percentile(p: float) -> float:
            idx = int(n * (p / 100.0))
            return latencies[min(idx, n - 1)]

        return {
            "p50_latency_ms": round(percentile(50), 2),
            "p90_latency_ms": round(percentile(90), 2),
            "p95_latency_ms": round(percentile(95), 2),
            "p99_latency_ms": round(percentile(99), 2),
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "throughput_rps": round(total_count / max(actual_duration, 0.001), 2),
            "total_requests": total_count,
            "failed_requests": failed_count,
            "error_rate_pct": round((failed_count / max(total_count, 1)) * 100, 2),
            "duration_sec": round(actual_duration, 2),
            "raw_data": {"samples_count": len(latencies)}
        }
