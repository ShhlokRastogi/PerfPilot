import os
import ast
import re
import urllib.parse
from typing import Dict, Any, List, Optional

IGNORED_DIRS = {
    "node_modules", ".git", ".venv", "venv", "__pycache__",
    "dist", "build", ".pytest_cache", ".gemini", "benchmarks"
}

class RepositoryIndexer:
    """
    Codebase Attribution & AST Indexer:
    Performs targeted static analysis using Python AST and symbol matching
    to discover route handlers, call sites, and source locations corresponding to target URLs.
    """

    @classmethod
    def get_path_from_url(cls, url: str) -> str:
        """Extracts normalized URL path component (e.g., '/api/products' or '/portal')."""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.path.rstrip("/") or "/"
        except Exception:
            return "/"

    @classmethod
    def locate_route_handler(cls, repo_path: str, target_url: str) -> Optional[Dict[str, Any]]:
        """
        Scans Python files via AST parsing to find route decorators matching the target URL path.
        """
        abs_repo = os.path.abspath(repo_path)
        if not os.path.exists(abs_repo):
            return None

        target_path = cls.get_path_from_url(target_url)
        path_segments = [p for p in target_path.split("/") if p]
        primary_segment = path_segments[-1] if path_segments else ""

        for root, dirs, files in os.walk(abs_repo):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if not file.endswith(".py") or file.startswith("test_"):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, abs_repo)

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        source_code = f.read()

                    tree = ast.parse(source_code, filename=rel_path)
                    lines = source_code.splitlines()

                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            for dec in node.decorator_list:
                                dec_str = ""
                                if isinstance(dec, ast.Call):
                                    # Inspect decorator arguments for route path strings
                                    for arg in dec.args:
                                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                            arg_val = arg.value.rstrip("/")
                                            if arg_val == target_path or (primary_segment and primary_segment in arg_val):
                                                start_line = node.lineno
                                                end_line = getattr(node, "end_lineno", start_line + 20)
                                                snippet = "\n".join(lines[start_line - 1:end_line])
                                                return {
                                                    "file_path": rel_path,
                                                    "symbol": node.name,
                                                    "start_line": start_line,
                                                    "end_line": end_line,
                                                    "snippet": snippet,
                                                    "matched_path": arg.value
                                                }
                except Exception:
                    continue

        return None

    @classmethod
    def collect_source_context(
        cls,
        repo_path: str,
        target_url: str = "",
        max_files: int = 5,
        max_lines_per_file: int = 250
    ) -> Dict[str, str]:
        """
        Collects targeted source context, prioritizing identified route handlers.
        """
        context: Dict[str, str] = {}
        abs_repo = os.path.abspath(repo_path)
        if not os.path.exists(abs_repo):
            return context

        # 1. First priority: Locate the specific route handler for target_url
        if target_url:
            handler = cls.locate_route_handler(repo_path, target_url)
            if handler:
                file_path = handler["file_path"]
                full_path = os.path.join(abs_repo, file_path)
                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[:max_lines_per_file]
                        context[file_path] = "".join(lines)
                except Exception:
                    pass

        # 2. Collect additional application source files
        for root, dirs, files in os.walk(abs_repo):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                if len(context) >= max_files:
                    break
                if file.endswith((".py", ".js", ".ts", ".sql")) and not file.startswith("test_"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, abs_repo)
                    if rel_path in context:
                        continue
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines = f.readlines()[:max_lines_per_file]
                            context[rel_path] = "".join(lines)
                    except Exception:
                        pass
            if len(context) >= max_files:
                break

        return context
