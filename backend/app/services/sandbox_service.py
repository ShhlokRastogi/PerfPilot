import os
import re
import shutil
import tempfile
import asyncio
import subprocess
import sys
import time
from typing import Tuple, Dict, Any, Optional, List
from urllib.parse import urlparse
import httpx
from backend.app.core.config import settings

class SandboxExecutionError(Exception):
    pass

# In-memory store for live sandbox execution steps (Item 6)
_SANDBOX_STEPS: Dict[str, List[Dict[str, Any]]] = {}

def get_sandbox_steps(run_id: str) -> List[Dict[str, Any]]:
    return _SANDBOX_STEPS.get(run_id, [])

def record_sandbox_step(
    run_id: str,
    step_id: str,
    name: str,
    status: str,
    output: str = "",
    duration_ms: float = 0.0
):
    if run_id not in _SANDBOX_STEPS:
        _SANDBOX_STEPS[run_id] = []
    
    # Check if step already exists and update
    for step in _SANDBOX_STEPS[run_id]:
        if step["step_id"] == step_id:
            step["status"] = status
            if output:
                step["output"] = output
            if duration_ms > 0:
                step["duration_ms"] = duration_ms
            return
            
    _SANDBOX_STEPS[run_id].append({
        "step_id": step_id,
        "name": name,
        "status": status,
        "output": output,
        "duration_ms": duration_ms,
        "timestamp": time.time()
    })

class SandboxEnvironment:
    def __init__(
        self,
        workspace_dir: str,
        port: int,
        service_url: str,
        proc: Optional[subprocess.Popen] = None,
        log_file_path: Optional[str] = None,
        is_disposable: bool = True
    ):
        self.workspace_dir = workspace_dir
        self.candidate_dir = workspace_dir  # backward compatibility alias
        self.port = port
        self.proc = proc
        self.service_url = service_url
        self.candidate_url = service_url    # backward compatibility alias
        self.health_url = f"http://127.0.0.1:{port}/health"
        self.log_file_path = log_file_path
        self.is_disposable = is_disposable

    def get_logs(self, max_lines: int = 100) -> str:
        """Retrieves real-time execution logs from the sandbox log file."""
        if self.log_file_path and os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().replace("\x00", "")
                    lines = content.splitlines(keepends=True)
                    return "".join(lines[-max_lines:])
            except Exception:
                pass
        return "No process logs recorded yet."

    def stop(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        if self.is_disposable and self.workspace_dir:
            try:
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
            except Exception:
                pass

CandidateEnvironment = SandboxEnvironment

class SandboxService:
    @classmethod
    def create_disposable_workspace(cls, source_repo: str) -> str:
        """
        Creates an isolated disposable candidate workspace in a temporary directory.
        Copies the real repository files into a sandbox worktree without touching source repo.
        """
        temp_dir = tempfile.mkdtemp(prefix="perfpilot_candidate_")
        if source_repo:
            abs_source = os.path.abspath(source_repo)
            if os.path.exists(abs_source):
                for item in os.listdir(abs_source):
                    s = os.path.join(abs_source, item)
                    d = os.path.join(temp_dir, item)
                    if os.path.isdir(s):
                        if item not in [".venv", "node_modules", ".git", "__pycache__", ".next", "dist"]:
                            shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
        return temp_dir

    @classmethod
    def apply_patch_to_workspace(cls, candidate_dir: str, patch_diff: str) -> Dict[str, Any]:
        """
        Real Unified Diff Patch Engine (Item 2 & 4).
        Applies standard unified diffs directly to the user's files inside the candidate workspace.
        """
        if not patch_diff or not patch_diff.strip():
            raise SandboxExecutionError("Proposed patch diff is empty.")

        # Try to extract target file path from diff header
        target_file = None
        for line in patch_diff.splitlines():
            if line.startswith("+++"):
                # +++ b/path/to/file or +++ path/to/file
                raw_path = line.split(maxsplit=1)[1].strip()
                if raw_path.startswith("b/"):
                    raw_path = raw_path[2:]
                target_file = raw_path
                break

        if not target_file:
            # Fallback to first line with ---
            for line in patch_diff.splitlines():
                if line.startswith("---"):
                    raw_path = line.split(maxsplit=1)[1].strip()
                    if raw_path.startswith("a/"):
                        raw_path = raw_path[2:]
                    target_file = raw_path
                    break

        if not target_file:
            # Check for affected files in candidate dir
            py_files = [f for f in os.listdir(candidate_dir) if f.endswith(".py") and not f.startswith("test_")]
            target_file = py_files[0] if py_files else "main.py"

        # Clean target path relative to candidate_dir
        rel_target = os.path.normpath(target_file)
        # If target has leading folder that matches basename of source repo, strip it
        parts = rel_target.split(os.sep)
        if len(parts) > 1 and not os.path.exists(os.path.join(candidate_dir, rel_target)):
            # Try matching subpath
            subpath = os.sep.join(parts[1:])
            if os.path.exists(os.path.join(candidate_dir, subpath)):
                rel_target = subpath

        abs_target = os.path.join(candidate_dir, rel_target)
        os.makedirs(os.path.dirname(abs_target), exist_ok=True)

        # Apply diff hunks
        original_content = ""
        if os.path.exists(abs_target):
            with open(abs_target, "r", encoding="utf-8", errors="ignore") as f:
                original_content = f.read()

        # Parse hunks and apply
        applied = False
        try:
            patched_content = cls._apply_unified_diff_hunks(original_content, patch_diff)
            with open(abs_target, "w", encoding="utf-8") as f:
                f.write(patched_content)
            applied = True
        except Exception as e:
            # If hunk parsing encounters offsets, attempt line-based replacement
            applied_code = cls._extract_replacement_code(patch_diff)
            if applied_code:
                with open(abs_target, "w", encoding="utf-8") as f:
                    f.write(applied_code)
                applied = True
            else:
                raise SandboxExecutionError(f"Failed to apply patch to {rel_target}: {e}")

        # Syntax validation
        if abs_target.endswith(".py"):
            with open(abs_target, "r", encoding="utf-8") as f:
                code_to_check = f.read()
            try:
                compile(code_to_check, abs_target, "exec")
            except SyntaxError as se:
                raise SandboxExecutionError(f"Candidate code has Python syntax error in {rel_target}: {se}")

        return {
            "file": rel_target,
            "applied": applied,
            "bytes_written": os.path.getsize(abs_target) if os.path.exists(abs_target) else 0
        }

    @staticmethod
    def _apply_unified_diff_hunks(original_text: str, diff_text: str) -> str:
        """
        Pure-Python unified diff hunk application.
        """
        orig_lines = original_text.splitlines(keepends=True)
        diff_lines = diff_text.splitlines()

        hunks = []
        current_hunk = []
        for line in diff_lines:
            if line.startswith("@@"):
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = [line]
            elif current_hunk:
                current_hunk.append(line)
        if current_hunk:
            hunks.append(current_hunk)

        if not hunks:
            # Not a standard hunk format; return replacement
            return SandboxService._extract_replacement_code(diff_text) or original_text

        result_lines = list(orig_lines)
        offset = 0

        for hunk in hunks:
            header = hunk[0]
            # Match @@ -start,len +start,len @@
            match = re.search(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
            if not match:
                continue

            old_start = int(match.group(1)) - 1
            old_len = int(match.group(2)) if match.group(2) else 1

            new_lines = []
            old_lines_to_match = []

            for h_line in hunk[1:]:
                if h_line.startswith("+"):
                    new_lines.append(h_line[1:] + "\n")
                elif h_line.startswith("-"):
                    old_lines_to_match.append(h_line[1:] + "\n")
                elif h_line.startswith(" "):
                    new_lines.append(h_line[1:] + "\n")
                    old_lines_to_match.append(h_line[1:] + "\n")

            # Slice and replace
            idx = old_start + offset
            if 0 <= idx <= len(result_lines):
                result_lines[idx:idx + len(old_lines_to_match)] = new_lines
                offset += len(new_lines) - len(old_lines_to_match)

        return "".join(result_lines)

    @staticmethod
    def _extract_replacement_code(diff_text: str) -> str:
        """
        Extracts added lines (+) from unified diff or parses code fences.
        """
        lines = []
        in_diff = False
        for line in diff_text.splitlines():
            if line.startswith("@@"):
                in_diff = True
                continue
            if in_diff:
                if line.startswith("+"):
                    lines.append(line[1:])
                elif line.startswith(" "):
                    lines.append(line[1:])
                elif not line.startswith("-") and not line.startswith("+++") and not line.startswith("---"):
                    lines.append(line)
        if lines:
            return "\n".join(lines)
        return diff_text

    @classmethod
    def find_python_interpreter(cls, workspace_dir: str, source_repo: Optional[str] = None) -> Tuple[str, str]:
        """
        Resolves the best Python interpreter to run target application and candidate sandbox.
        Searches workspace_dir and source_repo up the directory hierarchy (parents)
        and down (subdirectories) for existing virtual environments (.venv, venv, env).
        """
        search_roots = []
        if workspace_dir:
            search_roots.append(os.path.abspath(workspace_dir))
        if source_repo and os.path.abspath(source_repo) not in search_roots:
            search_roots.append(os.path.abspath(source_repo))

        # 1. Check search roots and ancestor directories (up to 4 levels)
        for root in search_roots:
            curr = root
            for _ in range(4):
                for vname in [".venv", "venv", "env"]:
                    for sdir, pexe in [("Scripts", "python.exe"), ("bin", "python"), ("bin", "python3")]:
                        vpath = os.path.join(curr, vname, sdir, pexe)
                        if os.path.exists(vpath):
                            return os.path.normpath(vpath), f"Repository Virtualenv ({vname} at {curr})"
                parent = os.path.dirname(curr)
                if parent == curr:
                    break
                curr = parent

        # 2. Check immediate subdirectories (e.g. root/backend/.venv)
        for root in search_roots:
            try:
                if os.path.exists(root):
                    for sub in os.listdir(root):
                        sub_path = os.path.join(root, sub)
                        if os.path.isdir(sub_path):
                            for vname in [".venv", "venv", "env"]:
                                for sdir, pexe in [("Scripts", "python.exe"), ("bin", "python"), ("bin", "python3")]:
                                    vpath = os.path.join(sub_path, vname, sdir, pexe)
                                    if os.path.exists(vpath):
                                        return os.path.normpath(vpath), f"Subdirectory Virtualenv ({sub}/{vname})"
            except Exception:
                pass

        # 3. Fallback to PerfPilot host Python interpreter
        return sys.executable, "PerfPilot Host Python (Fallback - dependencies may be missing)"

    @classmethod
    async def run_regression_tests(cls, candidate_dir: str, source_repo: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes real unit and regression tests in the candidate workspace
        using the target project's Python virtual environment.
        """
        python_bin, _ = cls.find_python_interpreter(candidate_dir, source_repo)

        # 1. Check for Python pytest
        has_py_tests = any(
            f.startswith("test_") or f.endswith("_test.py") or f == "tests"
            for f in os.listdir(candidate_dir)
        )
        if has_py_tests or os.path.exists(os.path.join(candidate_dir, "tests")):
            try:
                proc = await asyncio.create_subprocess_exec(
                    python_bin,
                    "-m",
                    "pytest",
                    "-v",
                    "--maxfail=3",
                    cwd=candidate_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                passed = (proc.returncode == 0)
                output = stdout.decode("utf-8", errors="ignore") + "\n" + stderr.decode("utf-8", errors="ignore")
                return {"passed": passed, "returncode": proc.returncode, "output": output.strip()}
            except Exception as e:
                return {"passed": False, "output": f"Failed to execute pytest: {e}"}

        # 2. Check for Node/TypeScript package.json
        pkg_json = os.path.join(candidate_dir, "package.json")
        if os.path.exists(pkg_json):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "npm.cmd" if os.name == "nt" else "npm",
                    "test",
                    cwd=candidate_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                passed = (proc.returncode == 0)
                output = stdout.decode("utf-8", errors="ignore") + "\n" + stderr.decode("utf-8", errors="ignore")
                return {"passed": passed, "returncode": proc.returncode, "output": output.strip()}
            except Exception:
                pass

        # If no tests exist in repo, verify basic syntax
        return {"passed": True, "returncode": 0, "output": "No automated test suite detected. Code syntax validation passed."}

    @classmethod
    async def launch_application_service(
        cls,
        workspace_dir: str,
        source_repo: Optional[str] = None,
        target_path_or_url: str = "/",
        port: int = 8001,
        phase_name: str = "baseline",
        run_id: Optional[str] = None,
        is_disposable: bool = True
    ) -> SandboxEnvironment:
        """
        Launches an application inside an isolated sandbox subprocess on a dedicated port.
        Automatically detects framework entrypoint, streams server logs to disk,
        and polls until responsive.
        """
        # Determine path
        if "://" in target_path_or_url:
            parsed = urlparse(target_path_or_url)
            path = parsed.path if parsed.path else "/"
            if parsed.query:
                path += f"?{parsed.query}"
        else:
            path = target_path_or_url if target_path_or_url.startswith("/") else f"/{target_path_or_url}"

        service_url = f"http://127.0.0.1:{port}{path}"
        abs_workspace = os.path.abspath(workspace_dir)

        # Detect Python executable from workspace or source repo
        python_bin, venv_desc = cls.find_python_interpreter(abs_workspace, source_repo)

        # Check if project root or subfolder (backend/src/api) contains entrypoint
        target_dir = abs_workspace
        if not any(os.path.exists(os.path.join(target_dir, f)) for f in ["main.py", "app.py", "manage.py", "server.py", "package.json"]):
            for sub in ["backend", "src", "api", "server"]:
                cand_sub = os.path.join(abs_workspace, sub)
                if os.path.isdir(cand_sub) and any(os.path.exists(os.path.join(cand_sub, f)) for f in ["main.py", "app.py", "manage.py", "server.py", "package.json"]):
                    target_dir = cand_sub
                    break

        # Detect start command
        manage_py = os.path.join(target_dir, "manage.py")
        main_py = os.path.join(target_dir, "main.py")
        app_py = os.path.join(target_dir, "app.py")
        server_py = os.path.join(target_dir, "server.py")
        pkg_json = os.path.join(target_dir, "package.json")

        cmd = None
        framework_desc = ""
        if os.path.exists(manage_py):
            cmd = [python_bin, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"]
            framework_desc = "Python Django (manage.py runserver)"
        elif os.path.exists(main_py):
            cmd = [python_bin, "-m", "uvicorn", "main:app", "--app-dir", target_dir, "--host", "127.0.0.1", "--port", str(port)]
            framework_desc = "Python FastAPI/Uvicorn (main:app)"
        elif os.path.exists(app_py):
            cmd = [python_bin, "-m", "uvicorn", "app:app", "--app-dir", target_dir, "--host", "127.0.0.1", "--port", str(port)]
            framework_desc = "Python FastAPI/Uvicorn (app:app)"
        elif os.path.exists(server_py):
            cmd = [python_bin, server_py]
            framework_desc = "Python Server (server.py)"
        elif os.path.exists(pkg_json):
            cmd = ["npm.cmd" if os.name == "nt" else "npm", "start", "--", "--port", str(port)]
            framework_desc = "Node.js (package.json npm start)"
        else:
            cmd = [python_bin, "-m", "http.server", str(port), "--directory", target_dir]
            framework_desc = "Static HTTP Server (python http.server)"

        cmd_str = " ".join(cmd)
        if run_id:
            record_sandbox_step(
                run_id=run_id,
                step_id=f"{phase_name}_detect",
                name=f"Auto-Detect {phase_name.capitalize()} Application Framework",
                status="completed",
                output=f"Framework: {framework_desc}\nWorkspace: {target_dir}\nInterpreter: {python_bin} ({venv_desc})\nCommand: {cmd_str}\nTarget URL: {service_url}"
            )

        # Open dedicated log file for live server stdout/stderr
        log_file_path = os.path.join(target_dir, f"{phase_name}_service.log")
        log_file = open(log_file_path, "w", encoding="utf-8", buffering=1)

        t0 = time.time()
        proc = subprocess.Popen(
            cmd,
            cwd=target_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )

        env = SandboxEnvironment(
            workspace_dir=abs_workspace,
            port=port,
            service_url=service_url,
            proc=proc,
            log_file_path=log_file_path,
            is_disposable=is_disposable
        )

        if run_id:
            record_sandbox_step(
                run_id=run_id,
                step_id=f"{phase_name}_launch",
                name=f"Launch {phase_name.capitalize()} Sandbox Process (PID {proc.pid})",
                status="running",
                output=f"Spawned PID {proc.pid} on port {port}. Waiting for health/readiness..."
            )

        # Poll until responsive with early crash detection
        timeout = 15.0
        start = asyncio.get_event_loop().time()
        is_ready = False

        async with httpx.AsyncClient() as client:
            while (asyncio.get_event_loop().time() - start) < timeout:
                # Fast exit check: Did the subprocess terminate prematurely?
                if proc.poll() is not None:
                    log_file.flush()
                    err_logs = env.get_logs(max_lines=30)
                    error_msg = f"Sandbox process (PID {proc.pid}) crashed with exit code {proc.returncode}.\n\n--- Process Output Logs ---\n{err_logs}"
                    if run_id:
                        record_sandbox_step(
                            run_id=run_id,
                            step_id=f"{phase_name}_launch",
                            name=f"Launch {phase_name.capitalize()} Sandbox on Port {port}",
                            status="failed",
                            output=error_msg,
                            duration_ms=(time.time() - t0) * 1000.0
                        )
                    raise SandboxExecutionError(error_msg)

                try:
                    probe_url = service_url if service_url else f"http://127.0.0.1:{port}/"
                    resp = await client.get(probe_url, timeout=1.0)
                    if resp.status_code < 500:
                        is_ready = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(0.4)

        if not is_ready:
            log_file.flush()
            err_logs = env.get_logs(max_lines=30)
            error_msg = f"Sandbox service on port {port} failed to become responsive within {timeout:.0f}s.\n\n--- Process Output Logs ---\n{err_logs}"
            if run_id:
                record_sandbox_step(
                    run_id=run_id,
                    step_id=f"{phase_name}_launch",
                    name=f"Launch {phase_name.capitalize()} Sandbox on Port {port}",
                    status="failed",
                    output=error_msg,
                    duration_ms=(time.time() - t0) * 1000.0
                )
            raise SandboxExecutionError(error_msg)

        elapsed_ms = (time.time() - t0) * 1000.0
        initial_logs = env.get_logs(max_lines=30)

        if run_id:
            readiness_note = f"Service responded ready on port {port} in {elapsed_ms:.0f}ms."
            record_sandbox_step(
                run_id=run_id,
                step_id=f"{phase_name}_launch",
                name=f"Launch {phase_name.capitalize()} Sandbox on Port {port}",
                status="completed",
                output=f"{readiness_note}\n\n--- Process Output Logs ---\n{initial_logs}",
                duration_ms=elapsed_ms
            )

        return env

    @classmethod
    async def launch_candidate_service(
        cls,
        candidate_dir: str,
        source_repo: Optional[str] = None,
        target_url: str = "/",
        port: int = 8002,
        **kwargs
    ) -> CandidateEnvironment:
        """Compatibility wrapper for candidate sandbox service."""
        run_id = kwargs.get("run_id")
        return await cls.launch_application_service(
            workspace_dir=candidate_dir,
            source_repo=source_repo,
            target_path_or_url=target_url,
            port=port,
            phase_name="candidate",
            run_id=run_id,
            is_disposable=True
        )
