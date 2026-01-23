Below is the **full, consolidated “SUPER PROMPT”** — clean, authoritative, and internally consistent — incorporating **everything** you specified:

* Go + Python hybrid architecture
* SvelteKit frontend
* **Tailwind CSS v4 + Vite**
* **Skeleton UI / Flowbite Svelte (not shadcn)**
* **Docker everywhere**
* **uv for Python**
* **bun for JS/Svelte**
* **Playwright MCP for screenshots (documentation evidence)**
* **Automatic diagram generation (Python diagrams / AWS Diagram MCP)**
* **Pandoc DOCX generation**
* Research-grade, explainable, encrypted-traffic-safe design

You can paste this **as-is** into Claude Code / Codex CLI / ChatGPT.

---

# 🚀 SUPER MASTER PROMPT

*(Hybrid Network Anomaly / DDoS Detection Platform)*

You are a **senior security systems architect and full-stack engineer**.
Design, implement, document, and package a **production-grade, research-ready network anomaly / DDoS detection platform** using a hybrid architecture:

* **Go** → high-speed data plane (packet capture & flow aggregation)
* **Python** → analytics plane (features, detection, evaluation)
* **SvelteKit** → operator dashboard (**Vite + Tailwind CSS v4**)

The system must work on **encrypted traffic using metadata only**.
No payload inspection. No TLS decryption.

---

## 0) GLOBAL OUTPUT RULES (MANDATORY)

1. Deliver a complete **monorepo** with runnable services.
2. Everything must be **Dockerized** and runnable via **Docker Compose**.
3. **Explainability is mandatory**: every alert must explain *why*.
4. Generate **full documentation** in Markdown **and** a compiled **DOCX** using **Pandoc** (already available).
5. Automatically generate **architecture diagrams**.
6. Use **Playwright MCP** to generate **UI screenshots** for documentation.
7. Package managers are **non-negotiable**:

   * **Python → uv**
   * **UI → bun**
8. Prefer deterministic, auditable, research-friendly designs.
9. Do not ask questions unless absolutely blocked.

---

## 1) HARD CONSTRAINTS

* No payload inspection; headers + flow metadata only.
* Support:

  * Live interface capture
  * PCAP replay
* Construct **bidirectional flows** via canonical 5-tuple normalization.
* Flow lifecycle must support:

  * Idle timeout
  * Max duration
* Ingestion **must not block** on analytics.
* Analytics downtime must **not stop capture**.
* All logs must be structured JSON.
* System must survive component restarts gracefully.

---

## 2) REQUIRED SERVICES

### A) Go Data Plane — `collector`

**Responsibilities**

* Capture packets (headers only)
* Timestamp packets
* Aggregate into bidirectional flows
* Finalize flows on timeout/close
* Emit `FlowEnded` events to the bus
* Perform non-blocking structured logging

---

### B) Transport Layer — `bus`

Choose and justify:

* **Primary**: Redis Streams **or** ZeroMQ
* **Alternative**: gRPC streaming

Design for:

* Backpressure
* Failure isolation
* Message durability (where applicable)

---

### C) Python Analytics Plane — `detector`

**Responsibilities**

* Consume flow summaries
* Feature extraction
* Deterministic rule-based detection
* Statistical anomaly detection (transparent methods)
* Fusion / decision engine
* Emit:

  * DetectionResult
  * AlertEvent
* Run evaluation experiments and metrics generation

---

### D) API Service — `api`

* REST + SSE endpoints for the dashboard
* Reads from storage
* Enforces auth + RBAC
* Exposes metrics and reports
* May be implemented in Python (FastAPI) or Go (justify choice)

---

### E) Dashboard — `ui`

**Framework**

* SvelteKit
* Vite
* Tailwind CSS **v4**
* Package manager: **bun**

**UI Library (NOT shadcn-style)**

* Default: **Skeleton UI**
* Alternative: **Flowbite Svelte**

---

## 3) MONOREPO STRUCTURE (REQUIRED)

```
/services
  /collector        (Go)
  /detector         (Python – uv)
  /api              (Python or Go)
/ui                 (SvelteKit – bun)
/schemas
/docs
  /diagrams
  /screenshots
  /spec
  /runbooks
  /threat-model
/tests
  /playwright
  /pcap
/deploy
  docker-compose.yml
  Dockerfiles
  .env.example
Makefile
```

---

## 4) PACKAGE MANAGEMENT (STRICT)

### Python (ALL Python services)

* Use **uv**
* `pyproject.toml`
* `uv.lock`
* Dockerfiles must:

  * install uv
  * `uv sync --frozen`
  * run services via `uv run`

❌ No pip
❌ No poetry
❌ No conda

---

### UI (SvelteKit)

* Use **bun**
* `bun install`
* `bun run build`
* Dockerfile must use bun for install & build

---

## 5) DOCKER REQUIREMENTS

Provide:

* Dockerfile per service
* One `docker-compose.yml` that starts:

  * collector
  * bus
  * detector
  * api
  * ui
  * storage (Postgres / ClickHouse / SQLite-in-container — justify)

Include:

* healthchecks
* `.env.example`
* clear run instructions

---

## 6) CANONICAL DATA CONTRACTS (`/schemas`)

Define **versioned JSON schemas + examples** for:

1. **EventEnvelope**
2. **FlowSummary**
3. **FeatureVector**
4. **DetectionResult**
5. **AlertEvent**
6. **AuditLogEntry**

Every DetectionResult must include:

* rules triggered
* anomaly score
* baseline comparison
* human-readable explanation

---

## 7) DETECTION DESIGN (EXPLAINABLE)

### Deterministic Rules

* SYN flood heuristics
* Port scanning patterns
* High fan-out / churn
* Rate-based thresholds

### Statistical Detection

Use transparent techniques:

* Rolling baselines
* Z-score / MAD
* EWMA drift

### Fusion Engine

* Explicit policy combining rules + anomaly scores
* Always produce “WHY”

---

## 8) STORAGE MODEL

Define and justify storage for:

* flows
* detections
* alerts + acknowledgements
* baselines
* experiments / evaluations
* audit logs

Include:

* retention policies
* indexes
* query patterns

---

## 9) API CONTRACT (REST + SSE)

Endpoints:

* `GET /flows`
* `GET /flows/{id}`
* `GET /alerts`
* `POST /alerts/{id}/ack`
* `GET /metrics`
* `GET /reports`
* `GET /config`
* `GET /health`
* `GET /ready`
* `GET /version`
* `GET /stream/alerts` (SSE)

Include request/response examples.

---

## 10) UI PAGES (MANDATORY)

1. Overview (health, ingest rate, latency)
2. Flows (filters + drill-down + explanation panel)
3. Alerts (live SSE + ack workflow)
4. Entities (IP/service baselines)
5. Reports (evaluation metrics)
6. Settings (read-only or admin)

---

## 11) PLAYWRIGHT MCP — SCREENSHOT GENERATION (MANDATORY)

**Primary purpose: documentation evidence**

Playwright MCP must:

1. Launch the system (Docker Compose)
2. Open the UI
3. Capture screenshots of:

   * Overview dashboard
   * Flows table
   * Flow explanation panel
   * Alerts page
   * Reports / evaluation page
   * Settings page (if present)
4. Save screenshots to:

```
/docs/screenshots/
```

With deterministic filenames:

* `overview.png`
* `flows.png`
* `flow_explanation.png`
* `alerts.png`
* `reports.png`

Screenshots must be:

* full-page where relevant
* consistent viewport
* clean (no dev overlays)

---

## 12) DIAGRAM GENERATION (MANDATORY)

Automatically generate diagrams into `/docs/diagrams` using:

* Python `diagrams`, Graphviz, PlantUML
* OR AWS Diagram MCP server

Required diagrams:

1. System context
2. Component architecture
3. Data flow
4. Sequence diagram
5. Deployment (docker-compose)
6. Threat boundaries

Save:

* source files
* rendered PNG/SVG

---

## 13) DOCUMENTATION + DOCX (MANDATORY)

Write full Markdown docs covering:

* Architecture
* Data contracts
* Detection logic
* API reference
* Deployment
* Operations
* Threat model
* Evaluation methodology

Embed:

* Generated diagrams
* Playwright screenshots

Compile everything into:

```
/docs/Network_Detection_Platform.docx
```

Using **Pandoc**.

---

## 14) AUTOMATION TARGETS

Provide Makefile targets:

* `make up`
* `make screenshots`
* `make diagrams`
* `make docs`
* `make test`

---

## 15) ACCEPTANCE CHECKLIST

Include a checklist verifying:

* PCAP replay determinism
* Non-blocking ingestion
* Explainable alerts
* Detector restart resilience
* SSE reconnect works
* Screenshots embedded in DOCX
* Diagrams generated
* DOCX builds successfully

---

## 16) FINAL OUTPUT

At the end, output:

* repo tree
* how to run (Docker)
* uv commands
* bun commands
* how to generate screenshots, diagrams, docs

Proceed to generate the **entire solution**.

---



Just say which.
