# Audit: noema-agent Current Architecture

**Date:** 2026-06-26  
**Branch:** `audit/noema-agent-current-architecture`  
**Closes:** rag-fish/noema-agent#17  
**Scope:** Read-only inventory — no source code changes

---

## 1. Repository Structure

```
noema-agent/
├── app/                         # Application package
│   ├── __init__.py
│   ├── main.py                  # FastAPI entrypoint; 3 endpoints
│   ├── models.py                # Pydantic request/response/error models
│   ├── executor.py              # Task execution + constraint gate wiring
│   ├── constraint_engine.py     # EPIC2: structural enforcement gate
│   └── logging_utils.py        # Structured JSON logging (4 event types)
├── tests/                       # pytest unit tests
│   ├── __init__.py
│   ├── test_phase2a.py          # Phase 2A compliance (models, executor)
│   ├── test_evidence_attachment.py  # X-4 evidence model + executor integration
│   └── test_epic2_constraint_engine.py  # EPIC2 constraint engine
├── uat/                         # Semi-automated UAT tooling
│   ├── runner.py                # LLM-judged scenario runner
│   ├── uat.sh                   # Shell orchestration script
│   ├── requirements-uat.txt
│   └── scenarios/
│       └── epic2_constraint_engine.yaml
├── docs/                        # Architecture and design documents
│   ├── architecture.md          # High-level component diagram
│   ├── architecture-boundaries.md  # Normative boundary specification
│   ├── router-policy-spec.md    # RouterRequest schema (design intent)
│   ├── epic2-constraint-engine-alignment.md
│   ├── integration-plan.md
│   ├── X5_Execution_Identity_Alignment.md
│   └── x2-implementation.md
├── artifacts/
│   └── context.md               # Session-bridging context artifact
├── Dockerfile                   # Multi-stage: builder / prod / dev
├── docker-compose.yml           # agent (prod) + agent-dev services
├── requirements.txt             # fastapi, uvicorn, pydantic (prod only)
├── requirements-dev.txt         # pytest, httpx, requests
├── test_api.py                  # FastAPI TestClient API tests
├── test_compliance.py           # Phase 2A + X-4 + X-5 compliance tests
├── GUARDRAIL-CONTRACT.md        # Normative execution boundary contract
└── README.md                    # Project documentation
```

**Major directories:**

| Directory | Purpose |
|-----------|---------|
| `app/` | Entire production application (5 Python files) |
| `tests/` | pytest unit tests (3 files, ~40 test functions) |
| `uat/` | LLM-judged semi-automated UAT (EPIC16 tooling) |
| `docs/` | Architecture and design documents (7 files) |
| `artifacts/` | Session-bridging context artifacts |

**Package structure:** Single-package application (`app`). No subpackages. No task registry abstraction exists yet — `execute_task()` in `executor.py` uses a direct `if task_type == "echo"` dispatch.

**Important configuration files:**

| File | Role |
|------|------|
| `Dockerfile` | Multi-stage prod/dev build |
| `docker-compose.yml` | Service definitions + env vars |
| `requirements.txt` | Production dependencies |
| `GUARDRAIL-CONTRACT.md` | Normative contract (not enforced at runtime) |

---

## 2. Server Startup

**Executable entrypoint:** `app/main.py`

**Framework:** FastAPI 0.115.x (ASGI), served by Uvicorn 0.32.x.

**Start command (production):**
```sh
uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log
```

**Start command (development / hot-reload):**
```sh
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Application lifecycle:** Standard FastAPI ASGI application — no startup/shutdown event hooks are registered. No lifespan context managers. No connection pool or state initialisation at startup.

**Configuration loading:** Configuration is loaded at module import time via `os.environ.get()` inside `app/constraint_engine.py`:

```python
_MAX_PAYLOAD_BYTES = int(os.environ.get("MAX_PAYLOAD_BYTES", 65536))
```

No other environment-variable-based configuration loading occurs. There is no config file, no `.env` loader, and no settings class.

**Environment variables (production-relevant):**

| Variable | Default | Effect |
|----------|---------|--------|
| `MAX_PAYLOAD_BYTES` | `65536` (64 KB) | Maximum accepted payload size |
| `ANTHROPIC_API_KEY` | _(none)_ | Required only by UAT runner (`uat/runner.py`) — not used by the server |

No secrets are consumed by the server process itself.

---

## 3. API Surface

The application exposes exactly **three HTTP endpoints**. There is no authentication middleware, no API key checking, and no rate limiting at the application layer.

### 3.1 `GET /`

| Property | Value |
|----------|-------|
| Method | GET |
| Path | `/` |
| Purpose | Service identity / basic health check |
| Authentication | None |

**Response (200 OK):**
```json
{
  "service": "noema-agent",
  "version": "3.0.0",
  "status": "ready",
  "description": "Stateless execution layer"
}
```

---

### 3.2 `GET /health`

| Property | Value |
|----------|-------|
| Method | GET |
| Path | `/health` |
| Purpose | Detailed health check; used by Docker HEALTHCHECK |
| Authentication | None |

**Response (200 OK):**
```json
{
  "status": "healthy",
  "executor": "ready",
  "supported_tasks": ["echo"]
}
```

**Notes:**
- The Docker HEALTHCHECK polls this endpoint every 30 s.
- `supported_tasks` is hardcoded — not derived from a registry.
- No dependency checks (no database, no external services).

---

### 3.3 `POST /invoke`

| Property | Value |
|----------|-------|
| Method | POST |
| Path | `/invoke` |
| Purpose | Main execution boundary — accepts and executes constrained tasks |
| Authentication | None |
| Request model | `InvocationRequest` (Pydantic, `extra="forbid"`) |
| Response model | `InvocationResponse` (Pydantic) |

**Request schema:**
```json
{
  "session_id":     "string (required)",
  "request_id":     "string (required)",
  "task_type":      "string (required)",
  "payload":        "object (default: {})",
  "timestamp":      "ISO-8601 string (optional)",
  "privacy_level":  "\"local\" | \"hybrid\" | \"cloud\" (optional)"
}
```

`trace_id` in the request body is **rejected** (422 Unprocessable Entity) — it is server-generated.

**Response schema (success):**
```json
{
  "session_id":        "string (echoed)",
  "request_id":        "string (echoed)",
  "trace_id":          "UUID (server-generated)",
  "status":            "\"success\"",
  "result":            "object",
  "error":             null,
  "timestamp":         "ISO-8601",
  "execution_time_ms": "integer",
  "evidence":          "array of EvidenceAttachment"
}
```

**Response schema (error):**
```json
{
  "session_id":        "string",
  "request_id":        "string",
  "trace_id":          "UUID",
  "status":            "\"error\"",
  "result":            {},
  "error": {
    "code":        "\"E-EXEC-001\" | ... | \"E-EXEC-005\"",
    "message":     "string",
    "recoverable": "boolean",
    "trace_id":    "UUID (matches response trace_id)",
    "timestamp":   "ISO-8601"
  },
  "timestamp":         "ISO-8601",
  "execution_time_ms": "integer",
  "evidence":          []
}
```

**Supported `task_type` values:** Only `"echo"` — returns payload unchanged.

**Error codes defined:**

| Code | Name | Recoverable |
|------|------|-------------|
| `E-EXEC-001` | UnsupportedTask | false |
| `E-EXEC-002` | ValidationError | false |
| `E-EXEC-003` | ExecutionFailure | false |
| `E-EXEC-004` | PrivacyViolation | false |
| `E-EXEC-005` | PayloadTooLarge | true |

**HTTP status codes:** The endpoint always returns **200 OK** for structurally valid requests, including execution errors. Schema violations return 422. There is no use of 4xx/5xx for execution-layer errors.

---

## 4. Routing

**No routing logic exists in noema-agent.**

The codebase explicitly and deliberately excludes routing. By design, routing is a client-side responsibility (see `docs/architecture-boundaries.md` §2.1 and `GUARDRAIL-CONTRACT.md` §Forbidden §1).

The only task dispatch that exists is a single `if task_type == "echo"` branch in `executor.py`. This is not a router — it is a minimal task dispatcher with one supported task.

There is no:
- Model router
- Tool router
- Workflow router
- Agent router
- Route decision record
- `selected_route` field in any response

The `docs/router-policy-spec.md` file contains a `RouterRequest` schema — this is a **design document for the client-side router** (NoesisNoema), not an implementation in noema-agent.

---

## 5. Policy

**No policy decision logic exists in noema-agent.**

Policy authority is explicitly assigned to the client layer (NoesisNoema) by the architecture. What noema-agent does have is a narrow **structural enforcement gate** (the ConstraintEngine), which is categorically distinct from policy:

### 5.1 ConstraintEngine (EPIC2 — structural enforcement only)

**File:** `app/constraint_engine.py`

Checks run in priority order before task dispatch:

| Check | Trigger | Error |
|-------|---------|-------|
| `_check_payload_size` | `json(payload)` > `MAX_PAYLOAD_BYTES` | `E-EXEC-005` |
| `_check_privacy_coherence` | `privacy_level == "local"` AND `task_type` in `_NETWORK_DEPENDENT_TASK_TYPES` | `E-EXEC-004` |

`_NETWORK_DEPENDENT_TASK_TYPES` is currently an **empty frozenset** — no task types are registered as network-dependent yet. The privacy coherence check therefore never fires in practice.

**What is absent:**
- No allow/deny rules
- No approval rules
- No role handling
- No policy conflict resolution
- No dynamic rule evaluation
- No policy store or configuration

---

## 6. Decision Logging

Structured logging exists and is the most mature observability feature in the codebase.

**File:** `app/logging_utils.py`

**Output format:** JSON, one event per log line, via Python's `logging` module with `format='%(message)s'`. Level is `INFO`.

**Log events emitted:**

| Event | Level | When | Required Fields |
|-------|-------|------|----------------|
| `invocation_started` | INFO | On every invocation, immediately after schema validation | `event_name`, `timestamp`, `trace_id`, `request_id`, `session_id`, `task_type` |
| `invocation_completed` | INFO | On every invocation return, success or error | `event_name`, `timestamp`, `trace_id`, `request_id`, `session_id`, `task_type`, `status`, `execution_time_ms` |
| `error_raised` | ERROR | On unsupported task or execution failure | `event_name`, `timestamp`, `trace_id`, `request_id`, `session_id`, `task_type`, `error_code`, `error_message`, `recoverable` |
| `constraint_rejected` | WARNING | On ConstraintEngine rejection | `event_name`, `timestamp`, `trace_id`, `request_id`, `session_id`, `task_type`, `error_code`, `constraint_name` |

**Trace identifiers:**

| Field | Source | Scope |
|-------|--------|-------|
| `trace_id` | Server-generated UUID at invocation entry | Per-invocation |
| `request_id` | Client-supplied, echoed verbatim | Per-request |
| `session_id` | Client-supplied, echoed verbatim | Per-session |

**Redaction:** Raw payload content is never logged. The `constraint_rejected` event explicitly excludes payload content per the observability contract.

**Gaps relative to GUARDRAIL-CONTRACT.md:** The contract specifies an `invocation_executed` event (distinct from `invocation_completed`), but this event is not implemented. In practice the two are merged into `invocation_completed`.

**Persistent log file:** `server.log` exists in the repo root (committed to the repository — likely a development artifact; not gitignored).

**No structured audit trail:** Logs are emitted to stdout/stderr only. There is no log aggregation, no log rotation configuration, no centralized log store, and no query interface. The trace_id allows manual reconstruction of a single invocation from log output but there is no tooling to do so.

---

## 7. Docker

**Dockerfile:** Multi-stage build with three named stages.

| Stage | Base | Contents | Default CMD |
|-------|------|----------|-------------|
| `builder` | `python:3.11-slim` | pip, venv, prod deps installed | _(not runnable)_ |
| `prod` | `python:3.11-slim` | venv + `app/` only; non-root user | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log` |
| `dev` | `prod` | adds dev deps + test files; hot-reload CMD | `uvicorn app.main:app ... --reload` |

**Security:** Production image runs as non-root user `noema` (created in Dockerfile). No pip or build tools in the final image.

**Exposed port:** `8000`

**Health check (Dockerfile):**
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

**docker-compose.yml:**

| Service | Image tag | Host port | Restart |
|---------|-----------|-----------|---------|
| `agent` | `noema-agent:prod` | `8000 → 8000` | `unless-stopped` |
| `agent-dev` | `noema-agent:dev` | `8001 → 8000` | `"no"` |

Both services set `MAX_PAYLOAD_BYTES=65536` via the `environment` key.

The `agent-dev` service mounts `./app` and `./tests` as volumes for hot-reload.

**Readiness:** No readiness probe is configured separately from the health check. The `start_period: 10s` provides a grace window before health-check failures count.

**Build commands:**
```sh
# Production
docker build --target prod -t noema-agent:prod .

# Dev/test
docker build --target dev -t noema-agent:dev .

# Run tests inside container
docker compose run --rm agent-dev pytest tests/ -v
```

---

## 8. Configuration

**Environment variables consumed by the server:**

| Variable | File | Default | Type | Effect |
|----------|------|---------|------|--------|
| `MAX_PAYLOAD_BYTES` | `app/constraint_engine.py` | `65536` | int | Payload size limit |

**Environment variables consumed by UAT tooling only (not server):**

| Variable | File | Required |
|----------|------|---------|
| `ANTHROPIC_API_KEY` | `uat/runner.py` | Yes (UAT only) |

**No secrets are used by the server.** There is no authentication, no database connection string, no API key validation.

**No config file format.** There is no `.env` template, no `config.yaml`, no settings class, and no pydantic `BaseSettings` usage.

**README discrepancy:** The README documents `trace_id` as an accepted request field and shows `"privacy_level": "local | hybrid | cloud (optional)"`. The actual implementation rejects `trace_id` in the request (X-5 enforcement), and accepts only `local`, `hybrid`, or `cloud` as enum values (not the string `"local | hybrid | cloud"`). These are documentation inaccuracies — out of scope for this audit.

---

## 9. Testing

### 9.1 Test files

| File | Type | Framework | Test count (approx.) |
|------|------|-----------|---------------------|
| `tests/test_phase2a.py` | Unit | pytest | ~13 functions |
| `tests/test_evidence_attachment.py` | Unit | pytest | ~9 functions |
| `tests/test_epic2_constraint_engine.py` | Unit | pytest | ~14 functions (in 5 classes) |
| `test_compliance.py` | API (TestClient) | pytest / FastAPI TestClient | ~13 functions |
| `test_api.py` | API (TestClient) | pytest / FastAPI TestClient | ~4 functions |

**Total:** approximately 53 test functions across 5 files.

### 9.2 Coverage areas

| Area | Covered |
|------|---------|
| InvocationRequest / InvocationResponse model validation | ✅ |
| Strict schema enforcement (`extra="forbid"`, missing fields) | ✅ |
| `trace_id` server-generation and uniqueness (X-5) | ✅ |
| Echo task success path | ✅ |
| Unsupported task error (E-EXEC-001) | ✅ |
| Payload size constraint (E-EXEC-005) | ✅ |
| Privacy coherence constraint (E-EXEC-004) | ✅ (via monkeypatching `_NETWORK_DEPENDENT_TASK_TYPES`) |
| ConstraintEngine statelessness guarantee | ✅ |
| `constraint_rejected` log event content | ✅ |
| Evidence attachment (X-4) | ✅ |
| Execution timing (`execution_time_ms`) | ✅ |
| Health endpoint | ✅ |
| Root endpoint | ✅ |

### 9.3 Coverage gaps

| Area | Status |
|------|--------|
| Concurrent invocation safety | Not tested |
| Docker build / health check | Not tested (no container-level CI) |
| `GET /` with unexpected query params | Not tested |
| Payload serialisation edge cases (non-ASCII, nested objects) | Partially tested |
| Coverage reporting | No `.coveragerc`, no `pytest-cov` in requirements |

### 9.4 UAT tooling

`uat/runner.py` is an LLM-judged semi-automated acceptance test runner. It sends real HTTP requests to a live server and asks Claude (`claude-sonnet-4-6`) to judge whether each response matches the scenario's stated expectation.

Scenario file: `uat/scenarios/epic2_constraint_engine.yaml` (covers EPIC2 constraint engine scenarios).

The UAT runner is not integrated with the Docker test command — it requires a separately started server and `ANTHROPIC_API_KEY`.

---

## 10. Architecture Comparison: Current State vs ADR-0001

ADR-0001 (Noema Architecture v0.1) defines noema-agent as the **governed orchestration server** responsible for policy routing, model routing, tool routing, a verifier, a decision log, approval requirements, and a stable app-facing route contract.

| Capability | Current State | Missing | Risk | Priority |
|------------|--------------|---------|------|----------|
| **Policy Router** | Absent. ConstraintEngine enforces structural-only rules (payload size, privacy coherence). No allow/deny policy evaluation. | Full policy evaluation layer with rule evaluation, allow/deny logic, and approval rules. | High — NoesisNoema has no server-side policy anchor; all policy is client-only. | P1 |
| **Model Router** | Absent. `task_type` dispatch is a single `if/elif` with one task (`echo`). No model selection, no model registry. | Model selection logic, model registry, routing rules per `task_type` / `privacy_level` / `intent`. | High — no path to LLM integration without a model routing layer. | P2 |
| **Tool Router** | Absent. No tool registry, no tool dispatch, no tool routing. | Tool registry, tool selection, tool invocation interface. | Medium — blocked until model router exists. | P3 |
| **Decision Log** | Partial. Structured JSON log events exist (`invocation_started`, `invocation_completed`, `constraint_rejected`, `error_raised`). `trace_id` propagated. No persistent store; no `audit_id`; no queryable trail. | Persistent decision log with `audit_id`, append-only guarantees, and queryable interface. | Medium — decisions are observable in dev but not auditable in production without a log collector. | P2 |
| **Approval Gate** | Absent. No approval concept exists in request or response schemas. | `required_approvals` field in route response; approval state machine; approval acknowledgement endpoint. | High — ADR-0001 and issue #18 both require `required_approvals` in the route response. | P1 |
| **Route Contract** | Absent. No `/v1/route` endpoint. The `POST /invoke` endpoint does not return a routing decision. `docs/router-policy-spec.md` defines a `RouterRequest` schema but it is a design doc, not an implementation. | Stable `/v1/route` endpoint returning `selected_route`, `reason`, `confidence`, `required_approvals`, `audit_id`. | Critical — this is the primary app-facing contract that NoesisNoema will connect to. | P0 |
| **Health Endpoint** | Present. `GET /health` returns `{"status": "healthy", "executor": "ready", "supported_tasks": ["echo"]}`. Docker HEALTHCHECK uses it. | Version field should be included for operational observability (minor). Otherwise complete for v0. | Low | P3 |
| **Docker Readiness** | Present and functional. Multi-stage Dockerfile, docker-compose with prod and dev services, health check configured, non-root user, no secrets. | No readiness probe separate from health check; no health check for `/v1/route` once added. | Low | P3 |
| **Observability** | Partial. Structured JSON logs with 4 event types, `trace_id`, `request_id`, `session_id`, `execution_time_ms`. No log aggregation, no Prometheus metrics, no distributed tracing integration, no `audit_id`. | Metrics endpoint (`/metrics`), distributed tracing headers, log shipper configuration, `audit_id` in log events. | Medium — adequate for development; insufficient for production multi-service observability. | P2 |

---

## 11. Recommendation

**Recommended next task: Route Contract v0**  
(Implements `POST /v1/route` endpoint — see issue #18)

**Justification:**

The Route Contract is the only capability that is both **critical priority** and **independently implementable right now** without prerequisite work.

1. **It is the primary integration surface.** NoesisNoema will connect to noema-agent through the route contract. Every other capability (model routing, tool routing, policy, approval) is meaningless without a stable endpoint to receive routing requests and return routing decisions. The Route Contract is the load-bearing wall of the governed orchestration server role.

2. **It can be implemented as a stub and iterated.** A v0 route endpoint that returns a structurally correct response with placeholder values (`selected_route`, `reason`, `confidence`, `required_approvals`, `audit_id`) satisfies the immediate integration requirement without requiring the policy engine, model router, or decision log to be complete. This is explicitly in scope for issue #18.

3. **It unblocks everything else.** Once `/v1/route` exists, the approval gate, model router, policy router, and decision log all have a concrete home to integrate into. Without it, all downstream capabilities have no endpoint to attach to.

4. **The existing infrastructure is ready.** FastAPI, Pydantic, Docker, and the structured logging layer are all in place. Adding a new endpoint with typed request/response models is a low-risk, well-understood operation given the existing codebase patterns.

The alternative candidates (Decision Log, Policy Router) require design decisions that depend on having the Route Contract schema defined first — the route contract response fields (`audit_id`, `required_approvals`) directly shape what the decision log must record and what the approval gate must enforce.

---

*End of audit. No source code was changed.*
