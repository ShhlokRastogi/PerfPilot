from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from backend.app.diagnostics.base import DiagnosticWorker
from backend.app.diagnostics.backend_worker import BackendDiagnosticWorker
from backend.app.diagnostics.database_worker import DatabaseDiagnosticWorker
from backend.app.diagnostics.frontend_worker import FrontendDiagnosticWorker

@dataclass
class RouterEvaluation:
    should_short_circuit: bool
    action: str  # "PROCEED_TO_DIAGNOSTICS" or "COMPLETE_SLA_MET"
    reason: str
    selected_workers: List[DiagnosticWorker] = field(default_factory=list)

class DeterministicRouter:
    """
    Deterministic Routing Layer:
    Enforces SLA short-circuit rules, selects diagnostic modules based on symptoms,
    and prevents unnecessary execution or diagnostic bloat.
    """

    @classmethod
    def evaluate_baseline(
        cls,
        baseline_metrics: Dict[str, Any],
        objectives: Dict[str, Any],
        target_type: str = "api"
    ) -> RouterEvaluation:
        """
        Evaluates baseline performance against SLA objectives:
        - Rule A: If baseline already satisfies SLA objectives, short-circuit and complete run.
        - Rule C: If SLA is breached, select only relevant, least invasive diagnostic workers.
        """
        p95_baseline = float(baseline_metrics.get("p95_latency_ms", 0.0))
        error_rate = float(baseline_metrics.get("error_rate_pct", 0.0))

        target_p95 = objectives.get("p95_latency_ms")
        max_error_rate = objectives.get("max_error_rate_pct", 5.0)

        # Check if baseline already meets SLA
        if target_p95 is not None and p95_baseline > 0:
            meets_p95 = p95_baseline <= float(target_p95)
            meets_error_rate = error_rate <= float(max_error_rate)

            if meets_p95 and meets_error_rate:
                return RouterEvaluation(
                    should_short_circuit=True,
                    action="COMPLETE_SLA_MET",
                    reason=(
                        f"Baseline performance already meets target SLA! "
                        f"Baseline p95: {p95_baseline:.1f}ms <= SLA: {float(target_p95):.1f}ms, "
                        f"Error rate: {error_rate:.2f}% <= Max: {float(max_error_rate):.2f}%. "
                        f"Candidate equals target; no optimization required."
                    ),
                    selected_workers=[]
                )

        # SLA breached or undefined: deterministically select diagnostic workers
        workers: List[DiagnosticWorker] = [BackendDiagnosticWorker(), DatabaseDiagnosticWorker()]

        # Only activate Frontend worker if target is a web application
        if target_type.lower() == "web":
            workers.append(FrontendDiagnosticWorker())

        return RouterEvaluation(
            should_short_circuit=False,
            action="PROCEED_TO_DIAGNOSTICS",
            reason=f"Baseline breached SLA (p95: {p95_baseline:.1f}ms vs target: {target_p95}ms). Dispatching {len(workers)} specialized diagnostic worker(s).",
            selected_workers=workers
        )
