# PerfPilot Developer & Architecture Guide

> **Target Audience:** Software engineers, platform engineers, and contributors joining the PerfPilot project.  
> **Prerequisites:** Python 3.11+, TypeScript/React, basic familiarity with HTTP load testing (k6) and ASGI/FastAPI.

---

## 1. Executive Summary: What is PerfPilot?

**PerfPilot** is an autonomous, evidence-driven performance engineering control plane. Unlike generic code-generation tools that guess performance optimizations from static code snippets, PerfPilot **empirically measures, investigates, patches, and proves** application performance improvements without human guesswork.

### The Core Problem PerfPilot Solves
Most AI coding tools suffer from two major flaws when applied to performance engineering:
1. **Hallucinated Gains**: They generate complex code rewrites and claim "this will be 3x faster" without any benchmark proof.
2. **Untracked Regressions**: A patch that speeds up a database query might break authentication, introduce SQL injection, or alter response contracts.

### The PerfPilot Solution
PerfPilot executes a deterministic, 12-stage closed loop:

$$\text{Workload Ingestion} \to \text{Baseline Auto-Sandbox} \to \text{k6 Load Test} \to \text{Diagnostic Routing} \to \text{Evidence Collection} \to \text{AST Attribution} \to \text{Patch Synthesis} \to \text{Safety Critic} \to \mathbf{Human\ Approval\ Gate} \to \text{Candidate Auto-Sandbox} \to \text{Verification} \to \text{Audit Report}$$

---

## 2. Core Architecture & Workflow

```
                                    ┌────────────────────────┐
                                    │  User Inputs Repo Path │
                                    │    (e.g., ./my-app)    │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ Auto-Sandbox Engine    │
                                    │ (Framework Detection)  │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ Baseline Sandbox (8001)│
                                    │ - Boots server process │
                                    │ - Streams live logs    │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                                    ┌────────────────────────┐
                                    │ k6 Workload Runner     │
                                    │ - Fires concurrent VUs │
                                    │ - Measures p95, RPS    │
                                    └───────────┬────────────┘
                                                │
                                                ▼
                             ┌──────────────────────────────────────┐
                             │    Deterministic Router              │
                             │ Does baseline meet SLA?              │
                             └───────────┬──────────────┬───────────┘
                                         │              │
                                   [YES] │              │ [NO]
                                         ▼              ▼
                              ┌───────────────┐  ┌────────────────────────┐
                              │ Short-Circuit │  │ Multi-Agent Diagnostic │
                              │   COMPLETE    │  │       Pipeline         │
                              └───────────────┘  └───────────┬────────────┘
                                                             │
                                                             ▼
                                                 ┌────────────────────────┐
                                                 │ Human Approval Gate    │
                                                 │ (Cryptographic Hash)   │
                                                 └───────────┬────────────┘
                                                             │ [Approved]
                                                             ▼
                                                 ┌────────────────────────┐
                                                 │ Candidate Sandbox(8002)│
                                                 │ - Clones disposable dir│
                                                 │ - Applies patch diff   │
                                                 │ - Runs regression tests│
                                                 └───────────┬────────────┘
                                                             │
                                                             ▼
                                                 ┌────────────────────────┐
                                                 │ Candidate Benchmark    │
                                                 │ - Verifies p95 delta   │
                                                 │ - Tears down sandboxes │
                                                 └───────────┬────────────┘
                                                             │
                                                             ▼
                                                 ┌────────────────────────┐
                                                 │ Deterministic Audit    │
                                                 │ Report & Verified Diff │
                                                 └────────────────────────┘
```

---

## 3. The Multi-Agent Diagnostic Pipeline

PerfPilot does **not** rely on a single monolithic LLM prompt. Instead, it coordinates specialized workers governed by strict application logic:

### Agent 0: The Deterministic Router (`backend/app/diagnostics/router.py`)
* **Role**: Pure Python decision engine (no LLM).
* **Short-Circuit Rule A**: If baseline measurements already satisfy all user SLA criteria (`p95 <= target_p95` and `error_rate <= max_error_rate`), the run halts and completes immediately with `COMPLETE_SLA_MET`. Candidate equals target; no unnecessary diagnostics are run.
* **Worker Selection (Rule C)**: Dispatches only relevant workers based on symptoms and target type.

### Agent 1: Backend Diagnostic Worker (`backend/app/diagnostics/backend_worker.py`)
* **Role**: Server telemetry and latency distribution investigator.
* **Capabilities**: Reads OpenTelemetry W3C trace context headers (`traceparent`, `x-trace-id`) to examine span durations. If OTel is not present on the target, cleanly falls back to external HTTP timing breakdowns with clear limitation records.

### Agent 2: Database Diagnostic Worker (`backend/app/diagnostics/database_worker.py`)
* **Role**: Data-layer bottleneck detector.
* **Capabilities**: Scans repository code using AST and static pattern matching for query loops (N+1 query detection), unbounded `.all()` queries without `LIMIT` or pagination, and unindexed filter keys.

### Agent 3: Frontend Diagnostic Worker (`backend/app/diagnostics/frontend_worker.py`)
* **Role**: Web application render investigator.
* **Capabilities**: When `target_type == "web"`, launches a headless Chromium instance via Playwright to measure Core Web Vitals (Largest Contentful Paint, Time to First Byte, DOM load timeline, and render-blocking scripts).

### Agent 4: Repository Attribution Worker (`backend/app/repository/indexer.py`)
* **Role**: AST codebase mapper.
* **Capabilities**: Parses Python files via the `ast` standard library to locate `@app.get(...)`, `@router.get(...)`, or controller route decorators matching the target URL path. Extracts the exact symbol, line range, and snippet without reading the entire repository.

### Agent 5: Patch Synthesis Engineer (`backend/app/optimization/synthesis_agent.py`)
* **Role**: Unified diff author.
* **Capabilities**: Translates empirical evidence records and validated source files into a minimal, production-grade unified diff (`--- a/` and `+++ b/`). Strict directives forbid hardcoded mock data, dummy returns, or modifying unrelated code.

### Agent 6: Safety Critic & Regression Evaluator (`backend/app/optimization/critic_agent.py`)
* **Role**: Adversarial reviewer.
* **Capabilities**: Evaluates the proposed patch for security vulnerabilities (e.g. SQL injection, unhandled nulls, concurrency deadlocks), scope containment, and generates a mandatory regression test plan.

---

## 4. Evidence Collection & Persistence Layer

All diagnostic findings are stored as first-class, immutable **`EvidenceRecord`** instances (`backend/app/evidence/schema.py`) and persisted in the SQLite `evidence_records` table (`EvidenceModel` in `backend/app/models/run.py`):

```python
class EvidenceRecord(BaseModel):
    evidence_id: str               # Unique UUID
    run_id: str                    # Associated run
    finding_id: Optional[str]      # Hypothesis link (e.g., H1)
    category: str                  # 'backend' | 'database' | 'frontend' | 'repository' | 'router'
    observation: str               # Factual empirical statement
    measured_values: Dict[str, Any]# e.g., {"p95_ms": 420.0, "queries": 150}
    unit: Optional[str]            # 'ms', 'req/s', 'queries'
    source_type: str               # 'opentelemetry' | 'sql_log' | 'playwright' | 'ast_parser' | 'http_metric'
    trace_id: Optional[str]        # Distributed trace ID
    span_id: Optional[str]         # OTel span ID
    timestamp: datetime            # Collection timestamp
    limitations: Optional[str]     # Known measurement constraints
```

**Architectural Rule:** Telemetry is immutable. The LLM can interpret evidence, but can never alter or overwrite raw measurement records.

---

## 5. Zero-Config Auto-Sandbox Engine

A major architectural feature of PerfPilot is that **users do NOT need to run their project on localhost beforehand**.

### How Framework Detection Works (`backend/app/services/sandbox_service.py`)
When a repository path is submitted, `SandboxService.launch_application_service`:
1. **Traverses Directory**: Inspects the root and subdirectories (`backend/`, `src/`, `api/`).
2. **Discovers Virtual Environments**: Checks for `.venv/`, `venv/`, or `env/` within the repository and binds directly to that interpreter (e.g. `.venv/Scripts/python.exe`), ensuring all project dependencies are loaded automatically.
3. **Detects Framework**:
   * **Django**: Detects `manage.py` $\to$ `python manage.py runserver 127.0.0.1:8001 --noreload`
   * **FastAPI / Uvicorn**: Detects `main.py` or `app.py` $\to$ `python -m uvicorn main:app --port 8001`
   * **Node.js**: Detects `package.json` $\to$ `npm start -- --port 8001`
   * **Static Web**: Falls back to `python -m http.server 8001`
4. **Captures Logs**: Pipes process stdout/stderr directly to `baseline_service.log` and streams it live to the `SandboxStepsConsole` UI.
5. **Polls Readiness**: Pings `http://127.0.0.1:8001/` until responsive before initiating load tests.

### Candidate Isolation & Zero-Copy Inheritance
When testing the candidate patch:
1. Clones source files into a temporary disposable folder (`tempfile.mkdtemp(prefix="perfpilot_candidate_")`).
2. **Excludes** heavy directories (`.venv/`, `node_modules/`, `.git/`) to execute in milliseconds.
3. Spawns the candidate process on port `8002` while **inheriting the source repo's interpreter**, giving it instant access to installed libraries without copying gigabytes.
4. After verification completes, the candidate process is killed and the temporary directory is deleted.

---

## 6. Security: The Human Approval Gate

To prevent autonomous AI agents from executing destructive code changes:
1. The synthesis agent produces a unified diff.
2. The server computes a cryptographic **SHA-256 hash** of the normalized diff:
   $$\text{Hash} = \text{SHA256}(\text{normalized\_diff})$$
3. The state transitions to `awaiting_approval`.
4. The user must review the diff in the UI and click **"Approve & Execute"**.
5. The API endpoint (`POST /api/runs/{run_id}/approval`) **requires the exact SHA-256 hash**.
   * If the client sends an altered patch or mismatched hash, the server rejects it with **HTTP 409 Conflict**.
   * If rejected, the run permanently transitions to `rejected`.

---

## 7. Repository Codebase Map

```
c:\D\Perfpilot\
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── runs.py                  # API endpoints (create run, status, metrics, evidence, approval)
│   │   │   └── config.py                # LLM model configuration & credentials status
│   │   ├── core/
│   │   │   ├── config.py                # Pydantic BaseSettings (loads .env, ALLOWED_HOSTS)
│   │   │   ├── database.py              # SQLite AsyncIO engine & sessionmaker
│   │   │   └── state_machine.py         # 13-state machine & transition validator
│   │   ├── diagnostics/
│   │   │   ├── base.py                  # Abstract DiagnosticWorker interface
│   │   │   ├── router.py                # Deterministic Router (Rule A, B, C)
│   │   │   ├── backend_worker.py        # Agent 1: OTel & HTTP probe
│   │   │   ├── database_worker.py       # Agent 2: N+1 & ORM static analyzer
│   │   │   └── frontend_worker.py       # Agent 3: Playwright browser diagnostics
│   │   ├── evidence/
│   │   │   └── schema.py                # EvidenceRecord Pydantic v2 data contract
│   │   ├── models/
│   │   │   └── run.py                   # SQLAlchemy ORM models (Run, BenchmarkMetric, EvidenceModel, etc.)
│   │   ├── optimization/
│   │   │   ├── prompts.py               # System prompts for all 6 agents (zero hardcoding)
│   │   │   ├── synthesis_agent.py       # Agent 5: Patch Synthesis Engineer
│   │   │   └── critic_agent.py          # Agent 6: Safety Critic & Regression Evaluator
│   │   ├── repository/
│   │   │   ├── indexer.py               # Agent 4: AST route indexer & context collector
│   │   │   └── validator.py             # Physical file existence & line validator
│   │   ├── schemas/
│   │   │   ├── run.py                   # Run creation and response schemas
│   │   │   ├── diagnosis.py             # Structured diagnosis output schema
│   │   │   └── report.py                # Final audit report schema
│   │   ├── services/
│   │   │   ├── benchmark_service.py     # k6 runner & async HTTP fallback engine
│   │   │   ├── diagnosis_service.py     # Multi-agent coordinator
│   │   │   ├── orchestration_service.py # End-to-end lifecycle orchestrator
│   │   │   ├── sandbox_service.py       # Auto-Sandbox launcher, hunk patcher, log capture
│   │   │   └── verification_service.py  # Deterministic p95/throughput delta evaluator
│   │   └── main.py                      # FastAPI application entrypoint
│   └── tests/
│       ├── test_backend.py              # Unit tests for state machine, formulas, approvals
│       └── test_e2e.py                  # Complete end-to-end autonomous lifecycle test
├── benchmarks/
│   ├── bin/                             # k6 binary location (ignored from git)
│   └── k6/
│       └── dynamic_workload_runner.js   # Universal k6 load test script
├── demo-app/
│   └── main.py                          # Built-in test target with intentional bottleneck
├── frontend/
│   ├── src/
│   │   ├── api/client.ts                # TypeScript API client
│   │   ├── components/
│   │   │   ├── ApprovalGate.tsx         # Human approval review modal
│   │   │   ├── DiffViewer.tsx           # Syntax-highlighted unified diff viewer
│   │   │   ├── LatencyChart.tsx         # Recharts quantile distribution chart
│   │   │   ├── MetricCard.tsx           # Before/after metric comparison card
│   │   │   └── SandboxStepsConsole.tsx  # Live terminal log viewer with step collapsible logs
│   │   ├── pages/
│   │   │   ├── NewAnalysisPage.tsx      # Run configuration page (repo path, route, SLA)
│   │   │   ├── OverviewPage.tsx         # Run history dashboard
│   │   │   └── RunDetailsPage.tsx       # Live execution monitor & Evidence Explorer
│   │   └── types/index.ts               # Shared TypeScript interfaces (EvidenceRecord, Run, etc.)
│   └── package.json
└── README.md
```

---

## 8. Quick Start for New Developers

### 1. Prerequisites
* Python 3.11+
* Node.js v20+ / npm v10+
* Git

### 2. Environment Setup
```bash
git clone https://github.com/ShhlokRastogi/PerfPilot.git
cd PerfPilot

# Create .env from example
cp .env.example .env
```

Add your LLM API key in `.env` (Groq is recommended for sub-second diagnosis):
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
LITELLM_MODEL=groq/openai/gpt-oss-120b
LITELLM_FALLBACK_MODEL=groq/qwen/qwen3.8-27b
ALLOWED_HOSTS=["*"]
```

### 3. Setup Python Backend
```bash
python -m venv backend/.venv

# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source backend/.venv/bin/activate

pip install -r backend/requirements.txt
```

### 4. Setup Frontend
```bash
cd frontend
npm install
cd ..
```

### 5. Running the Application
Open two terminal windows:

* **Terminal 1 (Backend API on Port 8080)**:
  ```bash
  .\backend\.venv\Scripts\python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
  ```
  API Docs: `http://localhost:8080/docs`

* **Terminal 2 (Frontend Dashboard on Port 3000)**:
  ```bash
  cd frontend
  npm run dev
  ```
  UI Dashboard: `http://localhost:3000`

---

## 9. Running Tests

Before submitting any code changes, ensure all test suites pass:

```bash
# 1. Backend Unit Tests & Full Autonomous Lifecycle E2E Test (9 tests)
.\backend\.venv\Scripts\python -m pytest backend/tests

# 2. Frontend Vitest Suite (3 tests)
cd frontend
npm test

# 3. Frontend TypeScript Typecheck
npx tsc -b
```

---

## 10. Design Philosophy & Golden Rules

When modifying or extending PerfPilot, always adhere to these rules:
1. **Never Fabricate Telemetry**: Every metric must come from k6, OpenTelemetry, Playwright, or direct HTTP measurements. If data is unavailable, mark it as `None` with an explicit limitation note.
2. **Zero Hardcoding**: Never hardcode domain roles, entity names, or canned diffs. Workloads must remain dynamic and schema-driven.
3. **Application Code Enforces Policy**: LLMs generate candidate hypotheses and diffs; application code enforces permissions, computes percentage changes, verifies regression tests, and determines verdicts.
4. **Clean Disposable Workspaces**: Never touch the user's source repository during candidate execution. All patches are tested in disposable temporary directories.
