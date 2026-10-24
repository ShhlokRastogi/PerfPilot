from typing import Dict, Any, Tuple
from backend.app.models.run import Verdict

class VerificationService:
    @staticmethod
    def calculate_percentage_change(baseline: float, candidate: float, lower_is_better: bool = True) -> float:
        """
        Calculates deterministic percentage improvement:
        If lower is better (e.g. latency): ((baseline - candidate) / baseline) * 100.0
        If higher is better (e.g. throughput): ((candidate - baseline) / baseline) * 100.0
        """
        if baseline <= 0.0:
            return 0.0
        if lower_is_better:
            return round(((baseline - candidate) / baseline) * 100.0, 2)
        else:
            return round(((candidate - baseline) / baseline) * 100.0, 2)

    @classmethod
    def evaluate_results(
        cls,
        baseline_metrics: Dict[str, Any],
        candidate_metrics: Dict[str, Any],
        objectives: Dict[str, Any],
        regression_passed: bool
    ) -> Tuple[Verdict, str, Dict[str, Any]]:
        """
        Deterministic, pure-Python verification evaluating regression status,
        metric improvements, and objective thresholds.
        """
        # If regression tests failed, verdict is automatically FAILED
        if not regression_passed:
            return (
                Verdict.FAILED,
                "Candidate patch broke functional regression tests. Rollback enforced.",
                {"regression_passed": False}
            )

        # Baseline and candidate numbers
        b_p95 = baseline_metrics.get("p95_latency_ms", 0.0)
        c_p95 = candidate_metrics.get("p95_latency_ms", 0.0)
        b_rps = baseline_metrics.get("throughput_rps", 0.0)
        c_rps = candidate_metrics.get("throughput_rps", 0.0)
        c_err = candidate_metrics.get("error_rate_pct", 0.0)

        # Check for invalid or inconclusive benchmarks
        if b_p95 <= 0.0 or c_p95 <= 0.0 or candidate_metrics.get("total_requests", 0) == 0:
            return (
                Verdict.INCONCLUSIVE,
                "Benchmark measurements were insufficient or zero requests were recorded.",
                {"is_conclusive": False}
            )

        p95_improvement_pct = cls.calculate_percentage_change(b_p95, c_p95, lower_is_better=True)
        rps_improvement_pct = cls.calculate_percentage_change(b_rps, c_rps, lower_is_better=False)

        # Evaluate target objectives
        target_p95 = objectives.get("p95_latency_ms", 250.0)
        min_speedup = objectives.get("min_speedup_factor", 1.5)
        max_error = objectives.get("max_error_rate_pct", 1.0)

        speedup_factor = round(b_p95 / max(c_p95, 0.001), 2)
        objectives_met = (
            c_p95 <= target_p95 and
            speedup_factor >= min_speedup and
            c_err <= max_error
        )

        details = {
            "p95_baseline_ms": b_p95,
            "p95_candidate_ms": c_p95,
            "p95_improvement_pct": p95_improvement_pct,
            "throughput_baseline_rps": b_rps,
            "throughput_candidate_rps": c_rps,
            "throughput_improvement_pct": rps_improvement_pct,
            "speedup_factor": speedup_factor,
            "min_speedup_required": min_speedup,
            "target_p95_ms": target_p95,
            "candidate_error_rate_pct": c_err,
            "max_allowed_error_pct": max_error,
            "regression_passed": True,
            "objectives_met": objectives_met,
            "is_conclusive": True
        }

        # Determine verdict
        if c_p95 > (b_p95 * 1.1):
            verdict = Verdict.REGRESSION
            summary = f"Performance regression detected: p95 latency increased from {b_p95}ms to {c_p95}ms (+{abs(p95_improvement_pct)}%)."
        elif objectives_met and p95_improvement_pct >= 25.0:
            verdict = Verdict.VERIFIED_IMPROVEMENT
            summary = f"Verified improvement! p95 latency reduced by {p95_improvement_pct}% ({b_p95}ms → {c_p95}ms, {speedup_factor}x speedup). All regression tests passed and objectives satisfied."
        elif p95_improvement_pct > 0.0:
            verdict = Verdict.NO_IMPROVEMENT
            summary = f"Marginal improvement of {p95_improvement_pct}%, but failed to meet minimum speedup objective ({speedup_factor}x < {min_speedup}x target)."
        else:
            verdict = Verdict.NO_IMPROVEMENT
            summary = f"No measurable performance improvement observed ({b_p95}ms vs {c_p95}ms)."

        return verdict, summary, details
