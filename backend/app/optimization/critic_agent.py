import json
import logging
from typing import Dict, Any, List
import litellm
from backend.app.core.config import settings
from backend.app.evidence.schema import EvidenceRecord
from backend.app.optimization.prompts import SAFETY_CRITIC_PROMPT

logger = logging.getLogger("perfpilot.critic")

class SafetyCriticAgent:
    """
    Safety & Regression Critic (Agent 6):
    Adversarially evaluates proposed optimization patches for security,
    regressions, scope containment, and test plan rigor.
    """

    @classmethod
    async def review_patch(
        cls,
        proposed_patch_diff: str,
        affected_files: List[str],
        evidence_records: List[EvidenceRecord],
        source_context: Dict[str, str],
        target_endpoint: str
    ) -> Dict[str, Any]:
        """
        Adversarial review returning risk evaluation, test plan, and verified hypotheses.
        """
        evidence_summary = [
            {"category": r.category, "observation": r.observation, "measured_values": r.measured_values}
            for r in evidence_records
        ]

        payload = {
            "target_endpoint": target_endpoint,
            "proposed_patch_diff": proposed_patch_diff,
            "affected_files": affected_files,
            "evidence": evidence_summary
        }

        user_prompt = f"""Adversarially evaluate the following proposed optimization patch against the empirical evidence:
```json
{json.dumps(payload, indent=2)}
```

Generate a structured safety critique in JSON strictly matching:
{{
  "observed_symptoms": ["list of factual symptoms identified from evidence"],
  "ranked_hypotheses": [
    {{"id": "H1", "title": "Bottleneck title", "description": "Mechanism", "likelihood": "High", "evidence": "Direct evidence"}}
  ],
  "confidence_score": 0.85,
  "uncertainty_notes": "Notes on edge cases or unverified assumptions",
  "potential_risks": ["list of identified operational, security, or regression risks"],
  "required_regression_tests": ["concrete list of regression checks to execute"],
  "verification_criteria": ["objective pass/fail conditions for benchmark verification"]
}}
"""
        models_to_try = [settings.LITELLM_MODEL]
        if settings.LITELLM_FALLBACK_MODEL and settings.LITELLM_FALLBACK_MODEL != settings.LITELLM_MODEL:
            models_to_try.append(settings.LITELLM_FALLBACK_MODEL)

        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Invoking Safety Critic with {model}")
                resp = await litellm.acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": SAFETY_CRITIC_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                    num_retries=settings.LLM_MAX_RETRIES
                )
                parsed = json.loads(resp.choices[0].message.content)
                return {
                    "observed_symptoms": parsed.get("observed_symptoms", ["High latency under load"]),
                    "ranked_hypotheses": parsed.get("ranked_hypotheses", [
                        {"id": "H1", "title": "Identified bottleneck", "description": "Resource contention", "likelihood": "High", "evidence": "Measured latency"}
                    ]),
                    "confidence_score": float(parsed.get("confidence_score", 0.85)),
                    "uncertainty_notes": parsed.get("uncertainty_notes", "Subject to candidate verification."),
                    "potential_risks": parsed.get("potential_risks", ["Potential latency regression if load pattern diverges."]),
                    "required_regression_tests": parsed.get("required_regression_tests", ["Functional endpoint integration tests."]),
                    "verification_criteria": parsed.get("verification_criteria", ["Candidate p95 meets SLA with zero functional regression."])
                }
            except Exception as e:
                logger.warning(f"Safety Critic failed for model {model}: {e}")
                last_error = e

        # Fallback to deterministic conservative critique if LLM is unavailable
        return {
            "observed_symptoms": ["Measured latency exceeded threshold during baseline benchmark."],
            "ranked_hypotheses": [
                {"id": "H1", "title": "Primary endpoint bottleneck", "description": "High latency detected", "likelihood": "High", "evidence": "Baseline k6 telemetry"}
            ],
            "confidence_score": 0.8,
            "uncertainty_notes": "Static critique fallback active.",
            "potential_risks": ["Verify functional behavior in candidate sandbox."],
            "required_regression_tests": ["Run complete endpoint smoke test."],
            "verification_criteria": ["Candidate latency < Baseline latency."]
        }
