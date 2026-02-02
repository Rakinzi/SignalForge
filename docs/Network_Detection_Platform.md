# SignalForge Network Detection Platform

## Overview
SignalForge is a production‑grade, research‑ready hybrid network anomaly and DDoS detection platform. It is designed to operate on **encrypted traffic using metadata only**, with **no payload inspection** and **no TLS decryption**. The architecture splits responsibilities across:

- **Go data plane (collector)** for high‑speed packet capture and flow aggregation
- **Python analytics plane (detector)** for feature extraction, rule‑based and statistical detection, and evaluation
- **Python API (api)** for REST + SSE endpoints with JWT auth and RBAC
- **SvelteKit UI (frontend)** for operator dashboards
- **Redis Streams** for event transport
- **PostgreSQL** for durable storage
- **Nginx** as edge reverse proxy for UI + API

This repository is a **monorepo** with fully dockerized services and a single **docker‑compose** stack.

---

## Architecture

### Diagrams
All diagrams below are generated using the Python `diagrams` package + Graphviz.

![System Context](diagrams/system_context.png)
![Component Architecture](diagrams/component_architecture.png)
![Data Flow](diagrams/data_flow.png)
![Sequence Diagram](diagrams/sequence.png)
![Deployment](diagrams/deployment.png)
![Threat Boundaries](diagrams/threat_boundaries.png)

### Data Flow

```
Network Packets
   ↓
Collector (Go)
   ↓ (FlowEnded events)
Redis Streams
   ↓
Detector (Python)
   ↓ (flows/detections/alerts/baselines/audit)
PostgreSQL
   ↓
API (FastAPI)
   ↓
UI (SvelteKit)
```

### Key Design Properties
- **Encrypted‑traffic safe:** only metadata from headers is used.
- **Non‑blocking ingestion:** collector emits flows asynchronously.
- **Fault isolation:** capture is not blocked by analytics downtime.
- **Graceful restarts:** Redis Streams + DB persistence preserve state.
- **Explainable alerts:** every detection has explicit rule + baseline context.
- **Structured logging:** JSON logs across services.

---

## Services

### 1) Collector (Go)
**Path:** `services/collector`

**Responsibilities**
- Live interface capture or PCAP replay
- Packet timestamping
- Canonical 5‑tuple normalization for **bidirectional flows**
- Flow lifecycle with **idle timeout** + **max duration**
- Flow summary emission to Redis Streams

**Key environment variables**
- `CAPTURE_MODE=auto|live|pcap`
- `CAPTURE_IFACE=eth0`
- `PCAP_PATH=tests/pcap/sample.pcap`
- `BPF_FILTER=tcp and port 80`
- `FLOW_IDLE_TIMEOUT=10s`
- `FLOW_MAX_DURATION=5m`
- `FLUSH_INTERVAL=2s`

---

### 2) Bus (Redis Streams)
**Service:** `redis`

Used as the primary transport layer. Supports backpressure and consumer groups. The collector writes `FlowEnded` events; detector consumes them.

---

### 3) Detector (Python)
**Path:** `services/detector`

**Responsibilities**
- Consume flow summaries from Redis Streams
- Feature extraction
- Rule‑based detection
- Statistical detection (rolling mean/variance + EWMA)
- Fusion engine with explainability
- Persist flows, detections, alerts, baselines, audit logs
- Periodic evaluation snapshots

**Detection logic**
- **Deterministic rules**
  - SYN flood heuristics
  - Port scan patterns
  - High fan‑out / churn
  - Low response ratio
- **Statistical detection**
  - Rolling baselines
  - Z‑score
  - EWMA drift

**Explainability**
Every detection result includes:
- Rules triggered
- Anomaly score
- Baseline comparison
- Human‑readable explanation

---

### 4) API (FastAPI)
**Path:** `services/api`

**Responsibilities**
- REST API for flows, alerts, baselines, detections, audit, reports
- SSE for live alerts
- JWT authentication
- RBAC with scope enforcement
- Structured JSON logging with request IDs

**Auth + RBAC**
- JWT tokens via `/auth/token`
- Scopes enforced per endpoint
- `GET /scopes` to introspect current permissions

**Default roles**
- Admin: full access
- Analyst: read + ack + reports
- Viewer: read‑only

---

### 5) UI (SvelteKit)
**Path:** `frontend`

Uses `VITE_API_URL=/api` by default and authenticates automatically with configured credentials. The UI is served behind Nginx and proxies `/api` to the backend.

---

## Data Contracts (`/schemas`)
Versioned JSON schemas are defined in `/schemas`:

1. `event_envelope.schema.json`
2. `flow_summary.schema.json`
3. `feature_vector.schema.json`
4. `detection_result.schema.json`
5. `alert_event.schema.json`
6. `audit_log_entry.schema.json`

These define the core event and storage contract between services.

---

## Storage Model (PostgreSQL)

**Tables**
- `flows` — canonical flow summaries
- `detections` — detection results with explainability
- `alerts` — actionable alerts with ack state
- `baselines` — rolling baselines by entity
- `audit_logs` — security and access events
- `evaluations` — periodic snapshot metrics

**Retention strategy (recommended)**
- `flows`: 7–30 days
- `detections`: 30–90 days
- `alerts`: 90+ days
- `baselines`: persistent
- `audit_logs`: 90+ days

---

## API Reference (Core)

### Health
- `GET /health`
- `GET /ready`
- `GET /version`

### Flows
- `GET /flows` (filters, cursor pagination)
- `GET /flows/{id}`

### Alerts
- `GET /alerts` (filters, cursor pagination)
- `POST /alerts/{id}/ack`
- `GET /stream/alerts` (SSE)

### Detections / Baselines / Audit
- `GET /detections`
- `GET /baselines`
- `GET /audit`

### Reports / Metrics / Config
- `GET /metrics`
- `GET /reports`
- `GET /config`

---

## Deployment

### Full stack (recommended)
```
docker compose -f deploy/docker-compose.yml up -d --build
```

### Access
- UI + API (via Nginx): `http://localhost:8088`
- API direct: `http://localhost:8000`

---

## Environment Configuration

Example in `deploy/.env.example`:

```
DATABASE_URL=postgresql+psycopg://signalforge:signalforge@postgres:5432/signalforge
JWT_SECRET=change-me
ADMIN_PASSWORD=admin
ANALYST_PASSWORD=analyst
VIEWER_PASSWORD=viewer
VITE_API_URL=/api
CAPTURE_MODE=auto
PCAP_PATH=tests/pcap/sample.pcap
NGINX_PORT=8088
```

---

## Screenshots & Diagrams

The following screenshots are captured from the live UI:

![Overview](screenshots/overview.png)
![Flows](screenshots/flows.png)
![Flow Explanation](screenshots/flow_explanation.png)
![Alerts](screenshots/alerts.png)
![Reports](screenshots/reports.png)
![Settings](screenshots/settings.png)

---

## Make Targets

```
make up
make diagrams
make screenshots
make docs
make test
```

---

## Acceptance Checklist (from prompt)

- [ ] PCAP replay determinism
- [ ] Non‑blocking ingestion
- [ ] Explainable alerts
- [ ] Detector restart resilience
- [ ] SSE reconnect works
- [x] Screenshots embedded in DOCX
- [x] Diagrams generated
- [x] DOCX builds successfully

---

## Quick Start

```
# Build + run full stack
make up

# Open UI
open http://localhost:8088
```

---

## Notes
- UI uses `/api` by default, proxied through Nginx.
- All detection logic uses metadata only — no payload inspection.
- The system is safe for encrypted traffic and TLS flows.
