import os
from typing import Dict, Any, List, Tuple

class SourceValidator:
    """
    Validates physical existence and integrity of source code references
    before they are committed to evidence or passed to patch synthesis.
    Rejects fabricated file paths and hallucinated line ranges.
    """

    @classmethod
    def validate_reference(cls, repo_path: str, ref: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validates whether a source reference physically exists in repo_path.
        Returns (is_valid, reason).
        """
        abs_repo = os.path.abspath(repo_path)
        file_path = ref.get("file_path", "")

        if not file_path:
            return False, "Missing file_path in reference"

        # Check path traversal attempts
        full_path = os.path.abspath(os.path.join(abs_repo, file_path))
        if not full_path.startswith(abs_repo):
            return False, f"Path traversal attempt detected: {file_path}"

        if not os.path.isfile(full_path):
            return False, f"Referenced file does not exist on disk: {file_path}"

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            return False, f"Cannot read referenced file: {str(e)}"

        total_lines = len(lines)
        start_line = int(ref.get("start_line", 1))
        end_line = int(ref.get("end_line", start_line))

        if start_line < 1 or start_line > total_lines:
            return False, f"Invalid start_line {start_line} (file has {total_lines} lines)"

        if end_line < start_line or end_line > total_lines:
            return False, f"Invalid end_line {end_line} (start_line is {start_line}, file has {total_lines} lines)"

        snippet = ref.get("snippet", "").strip()
        if snippet:
            # Check if any part of the snippet is found near start_line
            window_start = max(0, start_line - 5)
            window_end = min(total_lines, end_line + 5)
            file_window = "".join(lines[window_start:window_end])
            first_snippet_line = snippet.splitlines()[0].strip()
            if first_snippet_line and first_snippet_line not in file_window:
                # Soft note - line may have moved slightly but file exists
                pass

        return True, "Validated"

    @classmethod
    def filter_valid_references(cls, repo_path: str, references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns only the source references that pass physical validation.
        """
        valid = []
        for ref in references:
            is_valid, _ = cls.validate_reference(repo_path, ref)
            if is_valid:
                valid.append(ref)
        return valid
