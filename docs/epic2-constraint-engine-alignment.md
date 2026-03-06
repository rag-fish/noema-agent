# EPIC 2 — Constraint Engine Alignment

**Document Type:** Architecture Alignment  
**Version:** 1.0  
**Date:** 2026-03-06  
**Branch:** feature/epic2-constraint-engine  
**Status:** MANDATORY — Review before any EPIC2 code changes  
**References:**
- RAGFish: `design/invocation-boundary.md`
- RAGFish: `design/execution-flow.md`
- RAGFish: `design/router-decision-matrix.md`
- RAGFish: `design/security-model.md`
- RAGFish: `design/observability-standard.md`
- RAGFish: `design/memory-lifecycle.md`
- RAGFish: `design/error-doctrine.md`
- RAGFish: `design/EPIC1_Client_Authority_Hardening_Design.md`
- noema-agent: `GUARDRAIL-CONTRACT.md`
- noema-agent: `docs/X5_Execution_Identity_Alignment.md`

---

## 1. Summary of RAGFish Execution Boundaries

The RAGFish architecture defines strict, non-negotiable execution boundaries across three
layers. These boundaries are enforced hierarchically and are non-delegatable.

### 1.1 Authority Hierarchy

```
Human (Unconditional Veto)
    │
    ▼
Client Layer (Decision Authority)
  ├── Router             — decides route (local vs cloud)
  ├── Policy Engine      — evaluates constraints
  └── Constraint Evaluator — validates decision (pure function)
    │
    ▼ [Invocation Boundary]
    │
    ▼
Execution Layer (Execution Authority only — noema-agent)
  └── ExecutionCoordinator / Executor
    │
    ▼
Knowledge / Model Layer (Data Authority only)
  └── Local Executor / Cloud Executor / RAGpack
```

### 1.2 Binding Principles from Design Documents

**From `invocation-boundary.md` §5:**
> "The system MUST NOT: Modify system configuration, Persist memory outside declared path,
> Escalate routing silently, Execute undeclared external calls."

**From `execution-flow.md` §3, Step 3:**
> "The Router executes entirely within the Client boundary. The server does not make routing
> decisions."

**From `EPIC1_Client_Authority_Hardening_Design.md` §2.3:**
> "The Execution layer (noema-agent) is bound by the following constraints:
> It MUST NOT make routing decisions.
> It MUST NOT evaluate or override policy constraints.
> It MUST NOT self-initiate execution.
> It MUST NOT mutate the RoutingDecision received from the Client.
> It operates strictly within the ExecutionContext provided by the Client."

**From `router-decision-matrix.md` §1.1:**
> "The Router MUST execute client-side. The server MUST NOT make routing decisions.
> The server MAY validate routing decisions but MUST NOT override them."

**From `security-model.md` §4.6:**
> "No background execution, no recursive invocation, no tool self-discovery,
> no undeclared external calls."

---

## 2. How noema-agent Fits into the Execution Flow

noema-agent is the **Execution Layer** and sits exclusively on the server-side, after
the Invocation Boundary. It has no authority over routing, policy, or session management.

### 2.1 Position in the Flow

```
[Client]
  Human Input → Router → Policy Engine → Constraint Evaluator
                                               │
                          [Invocation Boundary — noema-agent entry point]
                                               │
                                       ┌───────▼────────┐
                                       │  noema-agent   │
                                       │  /invoke POST  │
                                       │                │
                                       │  1. Validate   │
                                       │     schema     │
                                       │  2. Generate   │
                                       │     trace_id   │
                                       │  3. Execute    │
                                       │     task       │
                                       │  4. Return     │
                                       │     response   │
                                       └────────────────┘
```

### 2.2 noema-agent's Exact Scope (Current State)

| Responsibility | Owned by noema-agent | Design Source |
|---|---|---|
| Schema validation of InvocationRequest | ✅ Yes | `invocation-boundary.md` §4 |
| Generating `trace_id` | ✅ Yes | `observability-standard.md` §3 |
| Measuring `execution_time_ms` | ✅ Yes | `observability-standard.md` §5 |
| Generating response `timestamp` | ✅ Yes | `invocation-boundary.md` §8 |
| Routing decisions | ❌ Never | `router-decision-matrix.md` §1.1 |
| Session management | ❌ Never | `memory-lifecycle.md` §4 |
| Policy evaluation | ❌ Never | `EPIC1` §2.3 |
| Model selection | ❌ Never | `GUARDRAIL-CONTRACT.md` §Forbidden |
| Persistence | ❌ Never | `memory-lifecycle.md` §8 |
| Background tasks | ❌ Never | `invocation-boundary.md` §3 |

---

## 3. Where the Agent-Side ConstraintEngine Must Sit

### 3.1 Definition

The agent-side **ConstraintEngine** (EPIC2 scope) is an **enforcement gate** — not a
decision-maker. It validates that the execution request does not violate structural
constraints that the Execution Layer is permitted to enforce.

It is distinct from the **Client-side Constraint Evaluator**, which makes policy decisions.

### 3.2 Architectural Position

```
InvocationRequest arrives at /invoke
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  EXECUTION LAYER (noema-agent)                          │
│                                                         │
│  Step 1: Pydantic Schema Validation (existing)          │
│          ↳ extra="forbid", field type checks            │
│                                                         │
│  Step 2: ConstraintEngine (EPIC2 — NEW)                 │
│          ↳ Structural constraint enforcement            │
│          ↳ fail-fast, no routing                        │
│          ↳ Returns E-EXEC-* errors if violated          │
│                                                         │
│  Step 3: Task Dispatch (existing)                       │
│          ↳ execute_task() in executor.py                │
│                                                         │
│  Step 4: Response Construction (existing)               │
└─────────────────────────────────────────────────────────┘
```

### 3.3 What ConstraintEngine MAY Enforce

These are enforcement checks, not routing decisions:

| Constraint Check | Error Code | Design Basis |
|---|---|---|
| Payload size limit | `E-EXEC-005` (PayloadTooLarge) | `GUARDRAIL-CONTRACT.md` §Allowed.2 |
| Privacy level coherence (reject forbidden combos) | `E-EXEC-004` (PrivacyViolation) | `security-model.md` §4.4 |
| Unsupported `task_type` | `E-EXEC-001` (UnsupportedTask) | existing executor |
| Malformed required fields | `E-EXEC-002` (ValidationError) | `error-doctrine.md` §2.3 |
| Execution-layer failures | `E-EXEC-003` (ExecutionFailure) | `error-doctrine.md` §2.2 |

### 3.4 What ConstraintEngine MUST NOT Do

The following are forbidden for the agent-side ConstraintEngine:

- ❌ Make routing decisions (e.g., "send to local vs cloud")
- ❌ Evaluate policy conflicts (Client authority only)
- ❌ Modify the `RoutingDecision` or task_type coming from the Client
- ❌ Perform probabilistic evaluation
- ❌ Mutate session state
- ❌ Trigger background execution
- ❌ Communicate with external services

**Authority invariant (AUTH-03):**
> "Pure Functions Must Not Cross Authority Boundaries. The Router, Policy Engine, and
> Constraint Evaluator must not be invoked server-side."
> — `EPIC1_Client_Authority_Hardening_Design.md` §8.5

The agent-side ConstraintEngine is NOT the same component as the Client-side Constraint
Evaluator. It is a lightweight enforcement gate that applies only structurally verifiable
rules.

---

## 4. Relationship with Client-Side ConstraintRuntime (NoesisNoema)

### 4.1 Separation of Concerns

| Component | Location | Role | Authority |
|---|---|---|---|
| **ConstraintRuntime** (NoesisNoema/Client) | Client-side | Policy evaluation, routing decision, conflict resolution | Client Authority |
| **ConstraintEngine** (noema-agent/Server) | Execution Layer | Structural enforcement gate, fail-fast rejection | Server enforcement only (no authority) |

### 4.2 Division of Responsibilities

**Client-side ConstraintRuntime is responsible for:**
- Evaluating `privacy_level` against execution context
- Resolving policy conflicts (e.g., privacy vs capability)
- Deciding whether to route to local or cloud
- Blocking cloud calls when `privacy_level == "local"`
- Constructing and finalizing `RoutingDecision`

**Agent-side ConstraintEngine is responsible for:**
- Verifying the request payload is structurally valid at the execution boundary
- Rejecting payloads that exceed size limits
- Rejecting requests with structurally incoherent field combinations
- Logging all rejections with `trace_id`

### 4.3 No Duplication Rule

The agent-side ConstraintEngine MUST NOT re-implement policy logic that belongs to the
Client-side ConstraintRuntime. Any constraint that requires knowledge of runtime state
(model availability, network state, token threshold) is exclusively a Client concern.

---

## 5. Enforcement Strategy

### 5.1 Principle: Fail-Fast, Reject Path

All constraint enforcement follows a strict fail-fast strategy:

1. **Check first, execute never**: Constraints are evaluated before any task execution begins.
2. **Structured rejection**: Any violation returns a typed `ErrorDetail` with an `E-EXEC-*`
   code immediately.
3. **No silent recovery**: There is no fallback, no retry, no re-routing on constraint failure.
4. **All rejections logged**: Every rejection emits an `error_raised` event with `trace_id`.

**From `error-doctrine.md` §4:**
> "The system must terminate execution immediately when an error occurs."
> "Prohibited behaviors: Silent retry, Implicit prompt rewriting, Hidden model escalation,
> Recursive execution loops."

### 5.2 Enforcement Pipeline (Proposed)

```
InvocationRequest
       │
       ▼
[Gate 1] Pydantic Schema Validation
       │ fail → 422 Unprocessable Entity (FastAPI automatic)
       ▼
[Gate 2] ConstraintEngine.check_payload_size()
       │ fail → E-EXEC-005, log error_raised, return InvocationResponse(error)
       ▼
[Gate 3] ConstraintEngine.check_privacy_coherence()
       │ fail → E-EXEC-004, log error_raised, return InvocationResponse(error)
       ▼
[Gate 4] Task Dispatch → execute_task()
       │ unsupported task → E-EXEC-001
       │ execution failure → E-EXEC-003
       ▼
InvocationResponse
```

### 5.3 Constraint Evaluation is a Pure Function

The ConstraintEngine must be implemented as:
- A pure function or a stateless class
- No I/O beyond returning a result
- No mutation of request or session state
- Deterministic: same input always produces same output

This is consistent with `EPIC1_Client_Authority_Hardening_Design.md` §6.5:
> "The Constraint Evaluator MUST be a pure function. It MUST NOT mutate system state.
> It MUST NOT trigger execution. It MUST NOT communicate with external services."

---

## 6. Logging Requirements (per observability-standard.md)

### 6.1 Required Events

noema-agent must emit the following structured JSON log events:

| Event | When | Required Fields |
|---|---|---|
| `invocation_started` | At entry, after schema validation | `event_name`, `timestamp`, `trace_id`, `session_id`, `request_id`, `task_type` |
| `constraint_rejected` | When ConstraintEngine rejects (NEW) | `event_name`, `timestamp`, `trace_id`, `session_id`, `request_id`, `task_type`, `error_code`, `constraint_name` |
| `invocation_completed` | At response return | `event_name`, `timestamp`, `trace_id`, `session_id`, `request_id`, `task_type`, `status`, `execution_time_ms` |
| `error_raised` | On any execution error | `event_name`, `timestamp`, `trace_id`, `session_id`, `request_id`, `task_type`, `error_code`, `error_message`, `recoverable` |

### 6.2 Field Rules from observability-standard.md §3

- `trace_id` MUST be generated by the Execution Layer at invocation entry (already implemented in X-5)
- `trace_id` MUST appear in all events for a given invocation
- `session_id` MUST appear in all events
- Raw `content` / `payload` MUST NOT appear in production logs
- `execution_time_ms` MUST appear in `invocation_completed`

### 6.3 Redaction Policy

**From `observability-standard.md` §6.1:**
> "Production logs MUST NOT include raw `content` (prompt text) by default."

For noema-agent:
- `payload` content MUST NOT be logged verbatim
- `evidence[].snippet` MUST NOT be logged verbatim
- Safe to log: `evidence_count`, `payload_key_count`, `task_type`, all identity fields

### 6.4 New Event: `constraint_rejected`

This event is introduced in EPIC2 to cover the new enforcement gate.

Required fields:
```json
{
  "event_name": "constraint_rejected",
  "timestamp": "ISO-8601",
  "trace_id": "uuid",
  "session_id": "string",
  "request_id": "string",
  "task_type": "string",
  "error_code": "E-EXEC-XXX",
  "constraint_name": "check_payload_size | check_privacy_coherence | ..."
}
```

---

## 7. Confirmation of Zero Persistence Requirement

### 7.1 Design Basis

**From `memory-lifecycle.md` §2:**
> "Memory is strictly session-scoped. There is no cross-session persistence.
> There is no autonomous long-term storage."

**From `memory-lifecycle.md` §4:**
> "Server may hold session data during active session only.
> Server must discard all session data upon: Timeout expiration, Explicit session termination."

**From `memory-lifecycle.md` §8 (Forbidden Behaviors):**
> "Automatic long-term summarization for retention, Silent memory compression,
> Cross-session carry-over, Memory-based routing without user visibility,
> Persistent vector store accumulation."

### 7.2 Zero Persistence Enforcement in noema-agent

noema-agent must maintain zero persistence as an absolute invariant:

| Prohibited Action | Reason | Source |
|---|---|---|
| Writing to database or file system | Persistence violation | `memory-lifecycle.md` §8 |
| Caching invocation results across requests | Cross-request state | `invocation-boundary.md` §3 |
| Accumulating constraint violation history | Implicit state | `memory-lifecycle.md` §8 |
| Maintaining any in-process mutable state | Session state violation | `GUARDRAIL-CONTRACT.md` |
| Background tasks that write data | Autonomous persistence | `invocation-boundary.md` §3 |

### 7.3 ConstraintEngine Zero-State Guarantee

The EPIC2 ConstraintEngine implementation MUST:
- Hold no instance state between invocations
- Accept only the `InvocationRequest` as input
- Write only to structured logs (append-only, passive)
- Return only a typed result (pass or `ErrorDetail`)
- Be safely callable from multiple concurrent requests (no shared mutable state)

---

## 8. Implementation Report: How EPIC2 Should Be Implemented in noema-agent

### 8.1 Scope Summary

EPIC2 introduces an agent-side **ConstraintEngine** — a stateless enforcement gate that
operates within the existing execution pipeline, between schema validation and task dispatch.

It does NOT introduce:
- Routing logic
- Session state
- Persistence
- Autonomous behavior
- Policy conflict resolution (Client authority)

### 8.2 Proposed File Structure

```
app/
├── main.py               # No changes required
├── models.py             # Add ConstraintViolation model (optional, or reuse ErrorDetail)
├── executor.py           # Wire ConstraintEngine.check() before task dispatch
├── constraint_engine.py  # NEW — pure function enforcement gate
└── logging_utils.py      # Add log_constraint_rejected() function
```

### 8.3 ConstraintEngine Interface Contract

```python
# app/constraint_engine.py

from app.models import InvocationRequest, ErrorDetail

def check_constraints(request: InvocationRequest) -> ErrorDetail | None:
    """
    Enforce structural execution constraints.

    Returns None if all constraints pass.
    Returns ErrorDetail if any constraint is violated.

    This is a pure function: no I/O, no state mutation, no side effects.
    """
```

Checks to implement in priority order:

1. **`check_payload_size`** — Reject if `len(str(request.payload))` exceeds configured limit
   - Error: `E-EXEC-005` (PayloadTooLarge), `recoverable=True`
   - Threshold: configurable, default 64KB

2. **`check_privacy_coherence`** — Reject structurally incoherent privacy combinations
   - Error: `E-EXEC-004` (PrivacyViolation), `recoverable=False`
   - Example: future network-dependent tasks rejected when `privacy_level == "local"`

3. **`check_task_type_known`** — Optionally pre-validate task_type against registry
   - Error: `E-EXEC-001` (UnsupportedTask), `recoverable=False`
   - Note: This may remain in executor.py if registry is co-located there

### 8.4 Integration in executor.py

```python
def execute_task(request: InvocationRequest) -> InvocationResponse:
    trace_id = str(uuid.uuid4())
    # ... log invocation_started ...

    # EPIC2: Constraint enforcement gate (fail-fast, before task dispatch)
    constraint_error = check_constraints(request)
    if constraint_error is not None:
        # log constraint_rejected
        # return structured error response
        ...

    # Existing task dispatch
    if request.task_type == "echo":
        ...
```

### 8.5 Non-Functional Requirements

| Requirement | Value | Source |
|---|---|---|
| Stateless | ConstraintEngine holds zero per-invocation state | `GUARDRAIL-CONTRACT.md` |
| Deterministic | Same request always produces same constraint result | `router-decision-matrix.md` §7 |
| Fail-fast | Constraint violation halts execution immediately | `error-doctrine.md` §4 |
| No persistence | No writes to any storage medium | `memory-lifecycle.md` §8 |
| Structured errors | All violations return typed `ErrorDetail` | `error-doctrine.md` §3 |
| Logged | All violations emit `constraint_rejected` event | `observability-standard.md` §4 |
| No routing | ConstraintEngine never selects execution path | `EPIC1` §8.5 AUTH-03 |

### 8.6 Tests Required

The following tests must be implemented to verify EPIC2 compliance:

| Test | Description |
|---|---|
| `test_payload_within_limit_passes` | Valid payload passes without error |
| `test_payload_exceeds_limit_returns_E_EXEC_005` | Oversized payload → E-EXEC-005 |
| `test_privacy_coherence_local_no_network_tasks` | Future: local + network task → E-EXEC-004 |
| `test_constraint_engine_is_stateless` | Multiple calls produce independent results |
| `test_constraint_engine_is_pure` | No side effects; no state between invocations |
| `test_constraint_rejected_log_emitted` | `constraint_rejected` event is logged |
| `test_existing_phase2a_tests_pass` | Regression: all prior tests remain green |

### 8.7 Open Boundary Decisions

The following decisions require explicit resolution before implementation:

| Decision | Options | Recommendation |
|---|---|---|
| Payload size threshold | Hardcoded vs config env var | Environment variable (`MAX_PAYLOAD_BYTES`), default 65536 |
| ConstraintEngine as class vs module | Stateless class vs module-level functions | Module-level functions (simpler, avoids instantiation state) |
| Privacy coherence scope | Only structural (no network calls) | Structural only — no I/O permitted |
| task_type pre-check location | ConstraintEngine vs executor.py | Keep in executor.py for now; move to registry in future EPIC |

---

## 9. Compliance Checklist

Before EPIC2 implementation is considered complete, the following must be verified:

### Architecture Compliance

- [ ] ConstraintEngine performs no routing decisions
- [ ] ConstraintEngine holds no state between invocations
- [ ] ConstraintEngine performs no I/O (no DB, no network, no file system)
- [ ] ConstraintEngine is invoked after schema validation and before task dispatch
- [ ] All constraint violations return structured `ErrorDetail` with `E-EXEC-*` code

### Observability Compliance

- [ ] `constraint_rejected` event is emitted for every constraint violation
- [ ] `trace_id` is present in all emitted events
- [ ] `payload` content is NOT logged verbatim
- [ ] `execution_time_ms` is measured from invocation entry (including constraint check time)

### Zero Persistence Compliance

- [ ] No writes to any storage medium
- [ ] No in-process mutable state accumulation
- [ ] No cross-request caching of constraint results
- [ ] ConstraintEngine safe for concurrent invocations

### Backward Compatibility

- [ ] All Phase 2A tests remain green
- [ ] All X-4 (Evidence) tests remain green
- [ ] All X-5 (Execution Identity) tests remain green
- [ ] InvocationRequest / InvocationResponse schemas unchanged

---

*End of EPIC 2 — Constraint Engine Alignment*

