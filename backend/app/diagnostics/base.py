from abc import ABC, abstractmethod
from typing import Dict, Any, List
from backend.app.evidence.schema import EvidenceRecord

class DiagnosticWorker(ABC):
    """
    Abstract interface for specialized diagnostic agents.
    Accepts structured investigation parameters and returns normalized evidence records.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the diagnostic worker."""
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        """Category: backend, database, or frontend."""
        pass

    @abstractmethod
    async def investigate(
        self,
        run_id: str,
        target_url: str,
        repo_path: str,
        baseline_metrics: Dict[str, Any]
    ) -> List[EvidenceRecord]:
        """
        Executes non-invasive diagnostic investigation and returns validated EvidenceRecords.
        Never fabricates telemetry or claims certainty beyond empirical observations.
        """
        pass
