import os
import json
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.run import Run, RunReport, Verdict
from backend.app.core.config import settings

class ReportService:
    @classmethod
    async def generate_and_persist_report(
        cls,
        db: AsyncSession,
        run_id: str,
        verdict: Verdict,
        summary: str,
        details: Dict[str, Any]
    ) -> RunReport:
        stmt = select(RunReport).where(RunReport.run_id == run_id)
        res = await db.execute(stmt)
        report = res.scalar_one_or_none()

        if not report:
            report = RunReport(
                run_id=run_id,
                verdict=verdict.value,
                summary=summary,
                p95_baseline_ms=details.get("p95_baseline_ms", 0.0),
                p95_candidate_ms=details.get("p95_candidate_ms", 0.0),
                p95_improvement_pct=details.get("p95_improvement_pct", 0.0),
                throughput_baseline_rps=details.get("throughput_baseline_rps", 0.0),
                throughput_candidate_rps=details.get("throughput_candidate_rps", 0.0),
                throughput_improvement_pct=details.get("throughput_improvement_pct", 0.0),
                regression_passed=details.get("regression_passed", True),
                objectives_met=details.get("objectives_met", False),
                is_conclusive=details.get("is_conclusive", True),
                details=details
            )
            db.add(report)
        else:
            report.verdict = verdict.value
            report.summary = summary
            report.p95_baseline_ms = details.get("p95_baseline_ms", 0.0)
            report.p95_candidate_ms = details.get("p95_candidate_ms", 0.0)
            report.p95_improvement_pct = details.get("p95_improvement_pct", 0.0)
            report.throughput_baseline_rps = details.get("throughput_baseline_rps", 0.0)
            report.throughput_candidate_rps = details.get("throughput_candidate_rps", 0.0)
            report.throughput_improvement_pct = details.get("throughput_improvement_pct", 0.0)
            report.regression_passed = details.get("regression_passed", True)
            report.objectives_met = details.get("objectives_met", False)
            report.is_conclusive = details.get("is_conclusive", True)
            report.details = details

        await db.commit()
        await db.refresh(report)

        # Export report artifact
        run_artifacts_dir = os.path.join(settings.ARTIFACTS_DIR, run_id)
        os.makedirs(run_artifacts_dir, exist_ok=True)
        report_file = os.path.join(run_artifacts_dir, "final_report.json")
        with open(report_file, "w") as f:
            json.dump({
                "run_id": run_id,
                "verdict": verdict.value,
                "summary": summary,
                "metrics": details
            }, f, indent=2)

        return report
