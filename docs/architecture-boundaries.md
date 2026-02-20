# Noesis Noema Architecture — noema-agent Boundaries

**Date:** February 20, 2026  
**Purpose:** Visual reference for architectural boundaries and integration points

---

## 1. System Architecture Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                         USER DEVICE (Client)                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  User Interface Layer                                       │  │
│  │  - Prompt input                                             │  │
│  │  - Response display                                         │  │
│  │  - Session controls                                         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Session Management Layer                                   │  │
│  │  - Session creation (generates session_id)                  │  │
│  │  - Session memory storage (authoritative)                   │  │
│  │  - 45-minute timeout enforcement                            │  │
│  │  - Session expiration handling                              │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Router Decision Matrix (Client-Side)                       │  │
│  │  - Evaluate privacy_level (local/cloud/auto)                │  │
│  │  - Token estimation                                         │  │
│  │  - Network state check                                      │  │
│  │  - Local model capability check                             │  │
│  │  - Deterministic route decision                             │  │
│  │  Output: route = "local" | "cloud"                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Orchestrator / Request Builder                             │  │
│  │  - Build InvocationRequest                                  │  │
│  │  - Attach session_id, request_id, timestamp                 │  │
│  │  - Select task_type based on router output                  │  │
│  │  - Package payload                                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
└───────────────────────────────┼───────────────────────────────────┘
                                │
                                │ POST /invoke (HTTPS)
                                │ InvocationRequest JSON
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│                    EXECUTION LAYER (noema-agent)                  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Invocation Boundary (/invoke endpoint)                     │  │
│  │  - Validate request schema (Pydantic)                       │  │
│  │  - Enforce privacy constraints (optional)                   │  │
│  │  - Log invocation (session_id, request_id, task_type)       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Task Registry                                              │  │
│  │  - Lookup task by task_type                                 │  │
│  │  - Retrieve BaseTask implementation                         │  │
│  │  - Fail if unsupported                                      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Task Executor                                              │  │
│  │  - Validate payload (task-specific)                         │  │
│  │  - Execute task.execute(payload)                            │  │
│  │  - Capture execution time                                   │  │
│  │  - Handle errors gracefully                                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Response Builder                                           │  │
│  │  - Build InvocationResponse                                 │  │
│  │  - Echo session_id, request_id                              │  │
│  │  - Include result or error                                  │  │
│  │  - Add execution metadata                                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                              ↓                                    │
└───────────────────────────────┼───────────────────────────────────┘
                                │
                                │ InvocationResponse JSON
                                │
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│                         CLIENT (User Device)                      │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Response Handler                                           │  │
│  │  - Parse InvocationResponse                                 │  │
│  │  - Update session memory (if applicable)                    │  │
│  │  - Reset 45-minute timeout                                  │  │
│  │  - Display to user                                          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 2. Responsibility Boundaries

### 2.1 Client/Orchestrator Scope (Upstream)

**Owns:**
- ✅ User interaction
- ✅ Session lifecycle (creation, timeout, termination)
- ✅ Session memory (authoritative storage)
- ✅ Router Decision Matrix execution
- ✅ Model selection
- ✅ Fallback logic
- ✅ Request ID generation (UUID)
- ✅ Timestamp generation

**Does NOT:**
- ❌ Execute tasks (delegates to noema-agent)
- ❌ Persist execution results long-term

---

### 2.2 noema-agent Scope (Execution Layer)

**Owns:**
- ✅ Invocation Boundary enforcement
- ✅ Task execution (deterministic)
- ✅ Input validation (schema)
- ✅ Privacy enforcement (guard rail)
- ✅ Structured response generation
- ✅ Execution logging (observability)
- ✅ Task registry management

**Does NOT:**
- ❌ Make routing decisions
- ❌ Select models
- ❌ Manage sessions
- ❌ Store session memory
- ❌ Enforce 45-minute timeout
- ❌ Persist data long-term
- ❌ Execute background tasks
- ❌ Self-modify or discover tools

---

## 3. Data Flow Diagram

```
User Input
   │
   ├─→ [Client: Create session_id]
   │
   ├─→ [Client: Apply Router Decision Matrix]
   │      ├─ Evaluate privacy_level
   │      ├─ Estimate tokens
   │      ├─ Check local model capability
   │      └─ Decide route: local | cloud
   │
   ├─→ [Orchestrator: Build InvocationRequest]
   │      {
   │        session_id: "abc-123",
   │        request_id: "req-456",
   │        task_type: "echo",
   │        payload: { "message": "Hello" },
   │        privacy_level: "local",
   │        timestamp: "2026-02-20T10:00:00Z"
   │      }
   │
   └─→ [POST /invoke] → noema-agent
          │
          ├─→ [Validate schema]
          │
          ├─→ [Privacy enforcement check]
          │
          ├─→ [Task registry lookup]
          │
          ├─→ [Execute task]
          │
          └─→ [Build response]
                 {
                   session_id: "abc-123",
                   request_id: "req-456",
                   status: "success",
                   result: { "message": "Hello" },
                   error: null,
                   executed_at: "2026-02-20T10:00:01Z",
                   execution_time_ms: 50
                 }
                 │
                 └─→ [Client: Update UI + session memory]
```

---

## 4. Session Lifecycle (Client-Owned)

```
┌─────────────────────────────────────────────────────────────┐
│  Client Session Management (45-minute timeout)              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Session Created (t=0)                                      │
│    ├─ Generate session_id (UUID)                           │
│    ├─ Initialize session memory container                  │
│    └─ Set last_activity_at = now()                         │
│                                                             │
│  Invocation 1 (t=5 min)                                    │
│    ├─ Send request with session_id to noema-agent          │
│    ├─ Receive response                                     │
│    ├─ Update session memory                                │
│    └─ Reset last_activity_at = now()                       │
│                                                             │
│  Invocation 2 (t=20 min)                                   │
│    ├─ Send request with session_id to noema-agent          │
│    ├─ Receive response                                     │
│    ├─ Update session memory                                │
│    └─ Reset last_activity_at = now()                       │
│                                                             │
│  ... (user inactive) ...                                   │
│                                                             │
│  Session Expired (t=65 min, 45 min since last activity)   │
│    ├─ Clear session memory                                 │
│    ├─ Invalidate session_id                                │
│    └─ Notify user (optional)                               │
│                                                             │
│  New Invocation Attempt (t=70 min)                         │
│    ├─ Detect expired session                               │
│    ├─ Create NEW session (new session_id)                  │
│    └─ Proceed with fresh context                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘

noema-agent DOES NOT participate in this lifecycle.
noema-agent only echoes session_id for traceability.
```

---

## 5. Router Decision Matrix (Client-Side)

```
┌─────────────────────────────────────────────────────────────┐
│  Router Decision Matrix (Deterministic Rules)               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input:                                                     │
│    - privacy_level: "local" | "cloud" | "auto"            │
│    - content: string (for token estimation)                │
│    - intent: optional ("informational", "analytical", etc.)│
│    - local_model_capability: object                        │
│    - network_state: "online" | "offline" | "degraded"     │
│                                                             │
│  Rules (Priority Order):                                   │
│                                                             │
│  1. PRIVACY_LOCAL                                          │
│     IF privacy_level == "local"                            │
│     THEN route = "local", fallback_allowed = false         │
│                                                             │
│  2. PRIVACY_CLOUD                                          │
│     IF privacy_level == "cloud"                            │
│     THEN route = "cloud", fallback_allowed = false         │
│                                                             │
│  3. AUTO_LOCAL                                             │
│     IF privacy_level == "auto"                             │
│        AND token_count <= token_threshold (4096)           │
│        AND local_model_available == true                   │
│        AND intent_supported_by_local == true               │
│     THEN route = "local", fallback_allowed = true          │
│                                                             │
│  4. AUTO_CLOUD                                             │
│     IF privacy_level == "auto"                             │
│        AND (none of above conditions met)                  │
│     THEN route = "cloud", fallback_allowed = false         │
│                                                             │
│  Output:                                                    │
│    - route: "local" | "cloud"                             │
│    - fallback_allowed: boolean                             │
│    - reason: string (for logging)                          │
│    - model: string (selected model identifier)             │
│                                                             │
└─────────────────────────────────────────────────────────────┘

noema-agent DOES NOT execute this logic.
noema-agent receives post-routing requests only.
```

---

## 6. Privacy Enforcement Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Privacy Enforcement (Defense in Depth)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Layer 1: Router (Client-Side) — PRIMARY                   │
│    IF privacy_level == "local"                             │
│    THEN route = "local", fallback_allowed = false          │
│    → Prevents cloud routing at decision time               │
│                                                             │
│  Layer 2: Orchestrator (Client-Side) — SECONDARY           │
│    IF privacy_level == "local"                             │
│    THEN do not include network-dependent task_types        │
│    → Prevents accidental cloud task selection              │
│                                                             │
│  Layer 3: noema-agent (Execution Layer) — GUARD RAIL       │
│    IF privacy_level == "local" AND task requires network   │
│    THEN return error "privacy_violation"                   │
│    → Prevents misconfiguration exploitation                │
│                                                             │
└─────────────────────────────────────────────────────────────┘

All layers log privacy decisions for audit trail.
```

---

## 7. Error Flow Diagram

```
Invocation Error Handling
   │
   ├─→ [noema-agent: Validation Error]
   │      └─→ Return: status="validation_error"
   │
   ├─→ [noema-agent: Unsupported Task]
   │      └─→ Return: status="unsupported_task", error="E-EXEC-001"
   │
   ├─→ [noema-agent: Privacy Violation]
   │      └─→ Return: status="privacy_violation", error="E-EXEC-004"
   │
   ├─→ [noema-agent: Execution Timeout]
   │      └─→ Return: status="execution_timeout", error="E-EXEC-003"
   │
   └─→ [noema-agent: Generic Error]
          └─→ Return: status="error", error=<message>

All errors are:
- Structured (JSON)
- Logged (with trace_id)
- Deterministic (no silent recovery)
- User-visible (no hidden failures)
```

---

## 8. Task Registry Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Task Registry (app/tasks/)                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  BaseTask (Abstract Interface)                             │
│    ├─ task_type: str (property)                            │
│    ├─ execute(payload: dict) -> dict (abstract)            │
│    └─ validate_payload(payload: dict) (optional)           │
│                                                             │
│  TaskRegistry (Singleton)                                  │
│    ├─ _tasks: Dict[str, BaseTask]                          │
│    ├─ register(task: BaseTask)                             │
│    ├─ get_task(task_type: str) -> BaseTask                 │
│    └─ list_tasks() -> List[str]                            │
│                                                             │
│  Registered Tasks:                                         │
│    ├─ EchoTask: task_type="echo"                           │
│    ├─ TransformTask: task_type="transform" (future)        │
│    └─ ValidateTask: task_type="validate" (future)          │
│                                                             │
│  Executor Integration:                                     │
│    def execute_task(request):                              │
│        task = registry.get_task(request.task_type)         │
│        result = task.execute(request.payload)              │
│        return InvocationResponse(...)                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Extension Process:
1. Implement BaseTask subclass
2. Add to registry in __init__.py
3. Write unit tests
4. Update documentation
```

---

## 9. Logging and Observability

```
┌─────────────────────────────────────────────────────────────┐
│  Structured Logging (JSON Format)                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Invocation Log Entry:                                     │
│  {                                                          │
│    "timestamp": "2026-02-20T10:00:00.123Z",                │
│    "level": "INFO",                                        │
│    "event": "invocation",                                  │
│    "session_id": "abc-123",                                │
│    "request_id": "req-456",                                │
│    "trace_id": "trace-789",                                │
│    "task_type": "echo",                                    │
│    "status": "success",                                    │
│    "execution_time_ms": 50,                                │
│    "privacy_level": "local"                                │
│  }                                                          │
│                                                             │
│  Error Log Entry:                                          │
│  {                                                          │
│    "timestamp": "2026-02-20T10:00:01.456Z",                │
│    "level": "ERROR",                                       │
│    "event": "execution_error",                             │
│    "session_id": "abc-123",                                │
│    "request_id": "req-789",                                │
│    "task_type": "unknown",                                 │
│    "error_code": "E-EXEC-001",                             │
│    "error_message": "Unsupported task type: unknown"       │
│  }                                                          │
│                                                             │
│  Privacy Enforcement Log:                                  │
│  {                                                          │
│    "timestamp": "2026-02-20T10:00:02.789Z",                │
│    "level": "WARN",                                        │
│    "event": "privacy_violation",                           │
│    "session_id": "abc-123",                                │
│    "request_id": "req-999",                                │
│    "privacy_level": "local",                               │
│    "task_type": "cloud_query",                             │
│    "action": "blocked"                                     │
│  }                                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Log Storage:
- Local file: server.log (development)
- Structured JSON (production)
- No raw prompt content (redacted)
- User-inspectable (transparency)
```

---

## 10. Integration Handshake Summary

### Client/Orchestrator → noema-agent

**Request Contract:**
```json
POST /invoke
{
  "session_id": "string (UUID)",
  "request_id": "string (UUID)",
  "task_type": "string (registered task)",
  "payload": "object (task-specific)",
  "privacy_level": "local | cloud | auto",
  "timestamp": "ISO 8601 datetime",
  "trace_id": "string (optional)"
}
```

**Response Contract:**
```json
HTTP 200 OK
{
  "session_id": "string (echoed)",
  "request_id": "string (echoed)",
  "status": "success | error | ...",
  "result": "object (task-specific)",
  "error": "string | null",
  "executed_at": "ISO 8601 datetime",
  "execution_time_ms": "number"
}
```

### Guarantees

**noema-agent guarantees:**
- ✅ Deterministic execution (same input → same output)
- ✅ No routing decisions
- ✅ No session management
- ✅ No persistent state
- ✅ Structured responses
- ✅ Traceability (logs all invocations)
- ✅ Privacy enforcement (guard rail)

**Client/Orchestrator guarantees:**
- ✅ Valid session_id generation
- ✅ Router decision completed before invocation
- ✅ Session timeout enforcement (45 minutes)
- ✅ Session memory management
- ✅ Request ID uniqueness

---

## 11. Deployment Topology

```
Production Deployment (Future State)

┌──────────────────────────┐
│  User Device (Client)    │
│  - Browser/Native App    │
│  - Router (WASM/JS)      │
│  - Session Manager       │
└──────────┬───────────────┘
           │
           │ HTTPS (TLS 1.3)
           │
           ↓
┌──────────────────────────┐
│  Load Balancer           │
│  - SSL Termination       │
│  - Rate Limiting         │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│  noema-agent Cluster     │
│  - Stateless instances   │
│  - Horizontal scaling    │
│  - No shared state       │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│  Observability Stack     │
│  - Structured logs       │
│  - Metrics (Prometheus)  │
│  - Tracing (optional)    │
└──────────────────────────┘
```

**Key Points:**
- noema-agent instances are stateless → easy horizontal scaling
- No database required → simple deployment
- No session affinity needed → load balance freely

---

## 12. Comparison: What Changed from X-2

| Aspect | X-2 (Minimal) | Enhanced (Integration) |
|--------|---------------|------------------------|
| Core contract | ✅ InvocationRequest/Response | ✅ Enriched with request_id, timestamp, privacy_level |
| Task execution | ✅ Hardcoded `if task_type == "echo"` | ✅ Registry-based dispatcher |
| Logging | ⚠️ Minimal | ✅ Structured JSON with all fields |
| Privacy enforcement | ❌ Not present | ✅ Optional guard rail |
| Error codes | ⚠️ Simple strings | ✅ Structured codes (E-EXEC-*) |
| Observability | ⚠️ Basic | ✅ Production-ready metrics |
| Extensibility | ⚠️ Modify core logic | ✅ Add tasks via registry |
| **Routing logic** | ✅ **Not present (correct)** | ✅ **Still not present (correct)** |
| **Session mgmt** | ✅ **Not present (correct)** | ✅ **Still not present (correct)** |
| **Stateless** | ✅ **Yes** | ✅ **Still yes** |

**Conclusion:** Enhanced version maintains all architectural constraints while adding production-ready features.

---

**End of Architecture Boundaries Document**

**Purpose:** Reference for integration teams to understand noema-agent's role and limits.

**Status:** ✅ Complete — Use as authoritative boundary specification.

