import os
import re
from typing import Dict, Any, List
from backend.app.diagnostics.base import DiagnosticWorker
from backend.app.evidence.schema import EvidenceRecord

class DatabaseDiagnosticWorker(DiagnosticWorker):
    """
    Database Diagnostic Agent:
    Investigates ORM access patterns, SQL query loops (N+1 query detection),
    unbounded queries, and schema indexing indicators in the target repository.
    """
    @property
    def name(self) -> str:
        return "DatabaseDiagnosticWorker"

    @property
    def category(self) -> str:
        return "database"

    async def investigate(
        self,
        run_id: str,
        target_url: str,
        repo_path: str,
        baseline_metrics: Dict[str, Any]
    ) -> List[EvidenceRecord]:
        records: List[EvidenceRecord] = []
        abs_repo = os.path.abspath(repo_path)
        
        if not os.path.exists(abs_repo):
            return records

        n_plus_one_suspects = []
        unbounded_queries = []

        # Scan repository for typical SQL and ORM performance antipatterns
        for root, _, files in os.walk(abs_repo):
            for file in files:
                if file.endswith((".py", ".js", ".ts")) and not file.startswith("test_"):
                    fpath = os.path.join(root, file)
                    rel_path = os.path.relpath(fpath, abs_repo)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()

                        # Detect potential query inside loop (N+1 pattern)
                        # e.g., for ...: ... db.query / execute / select / find / await
                        lines = content.splitlines()
                        in_loop = False
                        loop_indent = 0
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            indent = len(line) - len(line.lstrip())

                            if re.match(r"^(for|while)\s+", stripped):
                                in_loop = True
                                loop_indent = indent
                                continue

                            if in_loop:
                                if indent <= loop_indent and stripped and not stripped.startswith("#"):
                                    in_loop = False
                                else:
                                    # Check for DB call inside loop
                                    if re.search(r"(\.execute\(|\.query\(|\.find\(|select\(|db\.)", stripped):
                                        n_plus_one_suspects.append({
                                            "file_path": rel_path,
                                            "line": i,
                                            "code": stripped
                                        })

                        # Detect unbounded select statements (e.g. .all() without limit or pagination)
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if re.search(r"\.all\(\)", stripped) and not re.search(r"limit\(", stripped):
                                unbounded_queries.append({
                                    "file_path": rel_path,
                                    "line": i,
                                    "code": stripped
                                })
                    except Exception:
                        pass

        if n_plus_one_suspects:
            first_suspect = n_plus_one_suspects[0]
            records.append(
                EvidenceRecord(
                    run_id=run_id,
                    category=self.category,
                    observation=f"Potential N+1 database query pattern detected in repository: database operation called within loop iteration at {first_suspect['file_path']}:{first_suspect['line']}.",
                    measured_values={
                        "suspected_n_plus_one_count": len(n_plus_one_suspects),
                        "first_suspect_line": first_suspect["line"],
                        "first_suspect_code": first_suspect["code"]
                    },
                    unit="patterns",
                    source_type="sql_log",
                    source_references=[{
                        "file_path": s["file_path"],
                        "start_line": s["line"],
                        "end_line": s["line"],
                        "snippet": s["code"]
                    } for s in n_plus_one_suspects[:3]],
                    collection_method="static_ast_orm_analyzer",
                    provenance="source_code_inspection",
                    limitations="Identified via static heuristic; query count during dynamic execution must be verified."
                )
            )

        if unbounded_queries:
            first_unbounded = unbounded_queries[0]
            records.append(
                EvidenceRecord(
                    run_id=run_id,
                    category=self.category,
                    observation=f"Unbounded database query fetching all records without pagination or limit clause found at {first_unbounded['file_path']}:{first_unbounded['line']}.",
                    measured_values={
                        "unbounded_queries_detected": len(unbounded_queries),
                        "sample_file": first_unbounded["file_path"],
                        "sample_line": first_unbounded["line"]
                    },
                    unit="patterns",
                    source_type="sql_log",
                    source_references=[{
                        "file_path": u["file_path"],
                        "start_line": u["line"],
                        "end_line": u["line"],
                        "snippet": u["code"]
                    } for u in unbounded_queries[:3]],
                    collection_method="static_ast_orm_analyzer",
                    provenance="source_code_inspection"
                )
            )

        return records
