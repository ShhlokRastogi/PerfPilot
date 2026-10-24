# PerfPilot

> **Autonomous Evidence-Driven Performance Engineering Control Plane**  
> *Empirical measurement, diagnostic routing, AI-synthesized optimization, and deterministic verification.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)

PerfPilot is an autonomous performance engineering platform that investigates runtime performance bottlenecks, connects findings to source code, synthesizes targeted optimization patches, and **empirically proves** whether those patches improve performance without compromising functional correctness.

$$\text{Workload Ingestion} \longrightarrow \text{Baseline Auto-Sandbox} \longrightarrow \text{Evidence Collection} \longrightarrow \text{Source Attribution} \longrightarrow \text{Patch Synthesis} \longrightarrow \mathbf{Human\ Approval\ Gate} \longrightarrow \text{Candidate Auto-Sandbox} \longrightarrow \text{Deterministic Verification}$$

---

## 🌟 Key Features

* **Zero-Config Auto-Sandbox**: No need to manually start your server. PerfPilot auto-detects your application (FastAPI, Django, Express, static), boots it up in an isolated baseline sandbox, and streams process logs in real time.
* **Deterministic Router & Short-Circuiting**: If baseline measurements already satisfy your target SLA, the system immediately completes the run without wasting compute on unnecessary diagnostics.
* **6-Agent Multi-Agent Architecture**:
  1. **Deterministic Router**: Rule-based short-circuit and worker dispatcher.
  2. **Backend Worker**: OpenTelemetry W3C trace span analysis and latency breakdowns.
  3. **Database Worker**: Static AST inspection detecting N+1 query loops and unbounded reads.
  4. **Frontend Worker**: Playwright headless browser measuring LCP and render-blocking scripts.
  5. **AST Attribution Worker**: Pins runtime bottlenecks directly to source code decorators and functions.
  6. **Patch Synthesis & Critic Agents**: Authors minimal unified diffs and subjects them to adversarial security review.
* **First-Class Evidence Layer**: Normalized, validated `EvidenceRecord`s backed by Pydantic v2 and SQLite, recording raw measurements, trace IDs, and explicit limitations.
* **Cryptographic Human Approval Gate**: Patches are cryptographically locked using SHA-256 hashes. Any modification or tampering immediately invalidates execution.
* **Deterministic Verification**: Re-benchmarks the candidate in an isolated disposable sandbox on port `8002` to empirically prove latency reduction (e.g. p95 from 420ms to 35ms) before reporting.

---

## 📚 Documentation

For in-depth architectural specifications and module breakdowns, read the [**Developer & Architecture Guide**](docs/DEVELOPER_GUIDE.md).

---

## 🚀 Quick Start (Local Development)

### 1. Prerequisites
* **Python 3.11+**
* **Node.js v20+ & npm**
* **Git**

### 2. Clone & Configure
```bash
git clone https://github.com/ShhlokRastogi/PerfPilot.git
cd PerfPilot

# Create .env
cp .env.example .env
```

Add your LLM API key in `.env` (Groq is recommended for sub-second diagnosis):
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
LITELLM_MODEL=groq/openai/gpt-oss-120b
LITELLM_FALLBACK_MODEL=groq/qwen/qwen3.8-27b
ALLOWED_HOSTS=["*"]
```

### 3. Setup Backend
```bash
# Create and activate virtual environment
python -m venv backend/.venv

# Windows PowerShell:
.\backend\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 4. Setup Frontend
```bash
cd frontend
npm install
cd ..
```

### 5. Start the Stack
Open two terminal windows:

* **Terminal 1 (Backend API on Port 8080)**:
  ```bash
  .\backend\.venv\Scripts\python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8080 --reload
  ```
  API Docs (Swagger UI): [http://localhost:8080/docs](http://localhost:8080/docs)

* **Terminal 2 (Frontend Dashboard on Port 3000)**:
  ```bash
  cd frontend
  npm run dev
  ```
  Open your browser at: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing Your First Project

1. Navigate to [http://localhost:3000](http://localhost:3000) and click **"+ New Analysis"**.
2. To test the bundled demo:
   * **Repository Directory Path**: `demo-app`
   * **Endpoint Route Path**: `/api/products`
3. Click **"Start Performance Analysis"**.
4. Watch the **Sandbox Steps Console** expand in real time:
   * PerfPilot auto-detects the FastAPI application.
   * Auto-spawns the server on port `8001` and streams process logs.
   * Runs the baseline k6 load test (~420ms p95 latency due to an intentional loop).
   * Collects empirical telemetry records into the **Evidence Explorer**.
   * Identifies the bottleneck in `demo-app/main.py`.
   * Synthesizes a minimal unified diff patch and awaits your review.
5. Review the diff and click **"Approve & Execute Patch"**.
6. PerfPilot provisions a disposable candidate sandbox on port `8002`, applies the patch, verifies functional tests pass, and re-runs the benchmark to deterministically prove the speedup.

---

## 🛠️ Running the Automated Test Suite

```bash
# 1. Run all backend unit and end-to-end multi-agent lifecycle tests (9 tests)
.\backend\.venv\Scripts\python -m pytest backend/tests

# 2. Run frontend Vitest suite (3 tests)
cd frontend
npm test

# 3. Verify TypeScript builds with zero errors
npx tsc -b
```

---

## 📡 REST API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health, version, and database readiness |
| `POST` | `/api/runs` | Initialize a new performance analysis run |
| `GET` | `/api/runs` | List recent analysis runs |
| `GET` | `/api/runs/{id}/status` | Poll run lifecycle state machine status |
| `GET` | `/api/runs/{id}/metrics` | Retrieve baseline and candidate benchmark metrics |
| `GET` | `/api/runs/{id}/evidence` | Retrieve empirical `EvidenceRecord`s from diagnostic workers |
| `GET` | `/api/runs/{id}/sandbox-steps` | Stream live sandbox process logs and execution statuses |
| `GET` | `/api/runs/{id}/diagnosis` | Retrieve synthesized unified diff and safety critic review |
| `POST` | `/api/runs/{id}/approval` | Submit human approval gate decision (requires matching SHA-256) |
| `GET` | `/api/runs/{id}/report` | Retrieve final deterministic verdict, comparisons, and speedup |
| `GET` | `/api/runs/{id}/audit` | Retrieve complete timestamped audit log of state transitions |
| `DELETE` | `/api/runs` | Clear all past runs, metrics, and artifact files |

---

## 📄 License
MIT License.
