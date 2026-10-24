# PerfPilot

> **AI-Powered Application Performance Engineering Platform**  
> *Built for the AgentOps 2026 Hackathon*

PerfPilot is an automated, IT-infrastructure performance engineering platform that executes a closed-loop optimization workflow:

$$\text{Data Ingestion} \longrightarrow \text{Benchmarking} \longrightarrow \text{Intelligent Diagnosis} \longrightarrow \text{Fix Planning} \longrightarrow \mathbf{Human\ Approval\ Gate} \longrightarrow \text{Isolated Execution} \longrightarrow \text{Verification} \longrightarrow \text{Outcome Reporting}$$

---

## 1. Core Workflow & Architectural State Machine

Every analysis session transitions through validated, immutable state stages:

```
[ created ]
     ↓
[ validating ] ──────── (Target host whitelist, resource limits, paths)
     ↓
[ preparing_baseline ] ─ (Verify service health & readiness)
     ↓
[ benchmarking_baseline ] (k6 load generator / concurrent workload)
     ↓
[ diagnosing ] ───────── (Source code inspection + LiteLLM structured diagnosis)
     ↓
[ awaiting_approval ] ── [User Rejection] ──> [ rejected ] (Terminal: halted)
     ↓ [User Approves EXACT SHA-256 patch hash]
[ applying_patch ] ───── (Applied ONLY inside disposable candidate workspace)
     ↓
[ testing_candidate ] ── [Test Failure] ────> [ failed ] (Terminal: rollback)
     ↓ (Build & functional regression tests PASS)
[ benchmarking_candidate ] (Identical k6 workload under comparable conditions)
     ↓
[ verifying ] ────────── (Deterministic Python metric & SLA evaluation)
     ↓
[ completed ] ────────── (Terminal: verified_improvement | no_improvement | regression)
```

### Safety & Security Guarantees
- **Real Human Approval Gate:** No proposed patch can execute without explicit user approval. Approvals are cryptographically locked to the SHA-256 hash of the unified diff. Any modification immediately invalidates approval.
- **Strict Sandbox Isolation:** Candidate patches are never applied to source repositories or live environments. They run exclusively in disposable temporary workspaces.
- **Untrusted Context Guardrails:** LLM prompts strictly treat source code, repository files, and benchmark outputs as untrusted data, ignoring any embedded instruction overrides.
- **Deterministic Authority:** The LLM is used strictly for hypothesis ranking, root-cause explanation, and patch generation. Authoritative performance calculations, regression status, and verdicts are computed purely in deterministic Python code.

---

## 2. Technology Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 (Async), SQLite / PostgreSQL compatible.
- **Frontend Dashboard:** React 18/19, Vite, TypeScript, Tailwind CSS, Recharts, Lucide Icons.
- **LLM Gateway:** LiteLLM SDK (unified multi-provider support: OpenAI, Anthropic, Gemini) with graceful fallbacks and deterministic offline fixtures.
- **Load Testing & Verification:** k6 native binary load testing with high-precision async fallback runner; Playwright browser journeys.
- **Testing:** Pytest, pytest-asyncio, Vitest, React Testing Library.
- **Deployment:** Docker, Docker Compose.

---

## 3. Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js v20+ / npm v10+

### 1. Clone & Configure Environment
```bash
git clone https://github.com/agentops/perfpilot.git
cd perfpilot
cp .env.example .env
```

### 2. Set Up Python Backend
```bash
# Create virtual environment
python -m venv backend/.venv

# Activate (Windows PowerShell)
.\backend\.venv\Scripts\Activate.ps1
# Activate (macOS/Linux)
# source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Start the Demo Application
The bundled demo application features a deterministic, reproducible N+1 database query bottleneck:
```bash
python -m uvicorn main:app --app-dir demo-app --port 8001
```

### 4. Start the PerfPilot Backend API
In a new terminal window:
```bash
.\backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000 --reload
```
API Documentation will be accessible at: `http://localhost:8000/docs`

### 5. Start the React Frontend Dashboard
In a new terminal window:
```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```
Open your browser at: `http://localhost:3000`

---

## 4. Docker Deployment

Launch the entire stack (Backend, Frontend, and Demo App) with one command:
```bash
docker compose up --build
```
- Dashboard: `http://localhost:3000`
- API & Docs: `http://localhost:8000/docs`
- Demo Service: `http://localhost:8001/health`

---

## 5. Walkthrough: The Bundled Demo Scenario

1. Open `http://localhost:3000` and click **"+ New Analysis"**.
2. Click **"Reset to Bundled Demo (N+1 Query)"** to load the preset parameters:
   - Target URL: `http://127.0.0.1:8001/api/products`
   - Repo Path: `demo-app`
   - SLA Target: `p95 < 250ms`, `Min Speedup: 2.0x`
   - Workload: `10 VUs`, `8 seconds duration`
3. Click **"Launch PerfPilot Analysis"**:
   - Observe baseline benchmarks running in real time.
   - Baseline p95 latency is ~400ms due to 151 repetitive SQL queries per request.
4. **Inspect AI Diagnosis:**
   - The diagnosis engine analyzes `demo-app/main.py` lines 42–68.
   - Identifies the N+1 database roundtrips inside the loop.
   - Proposes a single relational `JOIN ... GROUP BY` SQL replacement.
5. **Approval Gate Test (Rejection):**
   - Click **"Reject Patch"** and provide feedback.
   - Observe the run immediately halt at terminal state `rejected`.
   - Verify that no candidate container or patch execution was performed.
6. **Approval Gate Test (Execution):**
   - Start another run, and when it reaches **Awaiting Human Approval**, click **"Approve & Execute Patch"**.
   - Watch PerfPilot apply the patch strictly inside a temporary disposable sandbox.
   - Watch regression tests execute (`test_demo_app.py` passes).
   - Watch candidate benchmarks execute on isolated port `8002`.
   - Candidate p95 latency drops to **~18ms** (>20x speedup!).
7. **Final Outcome & Auditable Report:**
   - Review before/after latency quantile bars and throughput charts.
   - Click **"Export Audit Report"** to download the JSON report containing cryptographic patch hashes, reviewer ID, timestamped audit events, and deterministic calculations.

---

## 6. Running the Automated Test Suite

```bash
# 1. Backend Unit & Security Gate Tests (7 tests)
.\backend\.venv\Scripts\python.exe -m pytest -v backend/tests/test_backend.py

# 2. End-to-End Autonomous Optimization Lifecycle Test
.\backend\.venv\Scripts\python.exe -m pytest -v backend/tests/test_e2e.py

# 3. Demo Application Functional Regression Tests (3 tests)
.\backend\.venv\Scripts\python.exe -m pytest -v demo-app/test_demo_app.py

# 4. Frontend Vitest & React Testing Library Tests (3 tests)
npm --prefix frontend test

# 5. Frontend Production Build Verification
npm --prefix frontend run build
```

---

## 7. API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | System health and database status |
| `POST` | `/api/runs` | Initialize a new performance analysis run |
| `GET` | `/api/runs` | List analysis runs |
| `GET` | `/api/runs/{id}` | Get run details and parameters |
| `GET` | `/api/runs/{id}/status` | Poll current state machine status |
| `GET` | `/api/runs/{id}/metrics` | Retrieve baseline and candidate benchmark metrics |
| `GET` | `/api/runs/{id}/diagnosis`| Retrieve AI diagnosis, hypotheses, and unified diff |
| `POST` | `/api/runs/{id}/approval` | Submit Human Approval (`approved` or `rejected`) |
| `GET` | `/api/runs/{id}/report` | Retrieve final deterministic verdict and comparisons |
| `GET` | `/api/runs/{id}/audit` | Retrieve complete timestamped audit event log |

---

## 8. License
MIT License. Created for AgentOps 2026.
