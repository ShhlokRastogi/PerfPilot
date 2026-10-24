from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

class HypothesisItem(BaseModel):
    id: Union[str, int] = Field(description="Unique hypothesis identifier, e.g. H1, H2, 1, 2")
    title: str = Field(description="Short title of the bottleneck hypothesis")
    description: str = Field(description="Detailed explanation of the theoretical root cause")
    likelihood: Union[str, float] = Field(description="Likelihood rating: High, Medium, Low, or float probability")
    evidence: str = Field(description="Direct benchmark or architectural evidence supporting this hypothesis")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v):
        return str(v)

    @field_validator("likelihood", mode="before")
    @classmethod
    def coerce_likelihood_to_str(cls, v):
        if isinstance(v, (int, float)):
            if v > 0.7:
                return "High"
            elif v > 0.3:
                return "Medium"
            else:
                return "Low"
        return str(v)

class CodeLocation(BaseModel):
    file_path: str = Field(description="Relative path to file with the bottleneck")
    start_line: int = Field(description="Start line number")
    end_line: int = Field(description="End line number")
    snippet: str = Field(description="Exact code snippet causing the performance issue")
    explanation: str = Field(description="Why this code is slow or suboptimal")

class StructuredDiagnosisOutput(BaseModel):
    summary: str = Field(description="Executive diagnosis summary")
    observed_symptoms: List[str] = Field(description="List of observed symptoms and benchmark indicators")
    ranked_hypotheses: List[HypothesisItem] = Field(description="Ranked root-cause hypotheses based on evidence")
    supporting_measurements: Dict[str, Any] = Field(description="Measurements cited directly from baseline benchmarks")
    supporting_code_locations: List[CodeLocation] = Field(description="Source code references identifying the root cause")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    uncertainty_notes: str = Field(description="Explanation of uncertainties, confounding factors, or missing data")
    proposed_patch_diff: str = Field(description="Standard unified diff or exact code replacement fixing the bottleneck")
    affected_files: List[str] = Field(description="List of files modified by the proposed patch")
    expected_benefits: str = Field(description="Estimated performance improvement, clearly labelled as an estimate")
    potential_risks: List[str] = Field(description="Potential side-effects, regressions, or operational risks")
    required_regression_tests: List[str] = Field(description="Specific test suites or validation checks to run")
    verification_criteria: List[str] = Field(description="Objective conditions required to verify improvement")

class DiagnosisResponse(BaseModel):
    id: int
    run_id: str
    summary: str
    symptoms: List[str]
    ranked_hypotheses: List[Dict[str, Any]]
    supporting_measurements: Dict[str, Any]
    supporting_code_locations: List[Dict[str, Any]]
    confidence_score: float
    uncertainty_notes: str
    proposed_patch_diff: str
    patch_hash: str
    affected_files: List[str]
    expected_benefit: str
    risks: List[str]
    regression_test_plan: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
