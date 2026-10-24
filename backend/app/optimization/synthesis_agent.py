import os
import json
import logging
from typing import Dict, Any, List, Optional
import litellm
from backend.app.core.config import settings
from backend.app.evidence.schema import EvidenceRecord
from backend.app.optimization.prompts import SYNTHESIS_ENGINEER_PROMPT

logger = logging.getLogger("perfpilot.synthesis")

class PatchSynthesisAgent:
    """
    Patch Synthesis Engineer (Agent 5):
    Translates validated evidence records and real repository source files
    into a minimal unified diff optimization patch.
    """

    @classmethod
    async def synthesize_patch(
        cls,
        evidence_records: List[EvidenceRecord],
        source_context: Dict[str, str],
        target_endpoint: str,
        user_objectives: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates patch diff and executive summary grounded in evidence and source code.
        """
        # Prepare evidence summary for prompt
        evidence_summary = [
            {
                "category": r.category,
                "observation": r.observation,
                "measured_values": r.measured_values,
                "source_references": r.source_references
            }
            for r in evidence_records
        ]

        payload = {
            "target_endpoint": target_endpoint,
            "user_objectives": user_objectives,
            "evidence": evidence_summary,
            "source_files": source_context
        }

        user_prompt = f"""Based on the following empirical evidence records and real source files:
```json
{json.dumps(payload, indent=2)}
```

Generate a minimal, production-grade optimization patch as a JSON object strictly matching:
{{
  "summary": "Executive summary of root cause and fix",
  "proposed_patch_diff": "Standard unified diff starting with '--- a/' and '+++ b/'",
  "affected_files": ["list of modified relative file paths"],
  "expected_benefits": "Estimated latency reduction or throughput increase (clearly marked as estimate)"
}}
"""
        models_to_try = [settings.LITELLM_MODEL]
        if settings.LITELLM_FALLBACK_MODEL and settings.LITELLM_FALLBACK_MODEL != settings.LITELLM_MODEL:
            models_to_try.append(settings.LITELLM_FALLBACK_MODEL)

        last_error = None
        for model in models_to_try:
            try:
                logger.info(f"Invoking Synthesis Agent with {model}")
                resp = await litellm.acompletion(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYNTHESIS_ENGINEER_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                    num_retries=settings.LLM_MAX_RETRIES
                )
                parsed = json.loads(resp.choices[0].message.content)
                return {
                    "summary": parsed.get("summary", "Performance optimization patch"),
                    "proposed_patch_diff": parsed.get("proposed_patch_diff", ""),
                    "affected_files": parsed.get("affected_files", []),
                    "expected_benefits": parsed.get("expected_benefits", "Estimated improvement based on bottleneck remediation")
                }
            except Exception as e:
                logger.warning(f"Synthesis Agent failed for model {model}: {e}")
                last_error = e

        raise RuntimeError(f"Synthesis Agent failed across all models: {last_error}")
