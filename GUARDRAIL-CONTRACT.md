# Guardrail Contract — noema-agent Execution Layer

**Version:** 2.0  
**Date:** February 20, 2026  
**Status:** Normative — Enforce Before MVP Integration

---

## Purpose

This contract defines the strict boundaries of noema-agent responsibilities.

**Violation of this contract invalidates architectural compliance.**

---

## Allowed Responsibilities

### 1. Accept Invocation Requests
- ✅ Receive structured InvocationRequest via `/invoke` endpoint
- ✅ Single entry point per invocation

### 2. Validate Request Schema
- ✅ Enforce required fields using Pydantic
- ✅ Reject undeclared fields (`extra = "forbid"`)
- ✅ Validate payload size limits

### 3. Execute Deterministic Tasks
- ✅ Dispatch to registered task implementations
- ✅ Execute based on task_type only
- ✅ No probabilistic behavior

### 4. Generate Structured Responses
- ✅ Return InvocationResponse with status and result
- ✅ Include execution metadata (timing, trace_id)

### 5. Echo Traceability Identifiers
- ✅ Echo session_id, request_id, trace_id in response
- ✅ Preserve end-to-end traceability

### 6. Emit Structured Logs
- ✅ Log invocation_started, invocation_executed, invocation_completed, error_raised
- ✅ Include required fields: event_name, timestamp, trace_id, session_id, request_id, task_type
- ✅ Use JSON format in production

### 7. Measure Execution Timing
- ✅ Capture execution start time
- ✅ Calculate execution_time_ms
- ✅ Include in response

### 8. Enforce Privacy Constraints (Guard Rail)
- ✅ Block network-dependent tasks if privacy_level == "local"
- ✅ Log privacy enforcement events
- ⚠️ This is enforcement, NOT routing

### 9. Return Structured Errors
- ✅ Use error codes (E-EXEC-001, E-EXEC-002, etc.)
- ✅ Include code, message, trace_id, timestamp, recoverable flag
- ✅ Log errors before returning

### 10. Fail Fast
- ✅ Return errors immediately
- ✅ No retry logic
- ✅ No silent recovery

---

## Forbidden Responsibilities

### 1. ❌ Routing Decisions
- MUST NOT decide local vs cloud execution
- MUST NOT select execution route
- **Reason:** Router lives client-side (router-decision-matrix.md)

### 2. ❌ Model Selection
- MUST NOT choose which model to invoke
- **Reason:** Orchestrator responsibility

### 3. ❌ Fallback Logic
- MUST NOT escalate to alternative execution strategies
- MUST NOT implement retry on failure
- **Reason:** Router handles fallback policy

### 4. ❌ Session Management
- MUST NOT create sessions
- MUST NOT validate 45-minute timeout
- MUST NOT enforce session expiration
- **Reason:** Client/Orchestrator responsibility (session-management.md)

### 5. ❌ Session Memory Storage
- MUST NOT store conversation history
- MUST NOT persist session state
- **Reason:** Stateless executor (memory-lifecycle.md)

### 6. ❌ Persistence
- MUST NOT write to database
- MUST NOT write to filesystem (except logs)
- **Reason:** Stateless execution layer

### 7. ❌ Background Execution
- MUST NOT schedule tasks
- MUST NOT spawn workers
- MUST NOT pre-compute responses
- **Reason:** Human sovereignty principle (invocation-boundary.md)

### 8. ❌ Recursive Invocation
- MUST NOT call itself
- MUST NOT trigger chained invocations
- **Reason:** Single invocation scope (invocation-boundary.md)

### 9. ❌ Autonomous Recovery
- MUST NOT retry failed tasks
- MUST NOT modify requests to "fix" errors
- **Reason:** No autonomous recovery (error-doctrine.md)

### 10. ❌ Tool Discovery
- MUST NOT dynamically discover tools
- MUST NOT register tools at runtime
- **Reason:** Deterministic execution

### 11. ❌ Silent Failure
- MUST NOT suppress errors
- MUST NOT hide execution failures
- **Reason:** Fail-fast policy (error-handling.md)

### 12. ❌ Configuration Mutation
- MUST NOT modify system configuration during execution
- **Reason:** Invocation boundary rules

### 13. ❌ Prompt Rewriting
- MUST NOT modify user input
- MUST NOT transform task payload
- **Reason:** Human sovereignty

### 14. ❌ Cross-Session Correlation
- MUST NOT link data across sessions
- MUST NOT profile users
- **Reason:** Session-scoped memory only (memory-lifecycle.md)

---

## Mandatory Interface Requirements

### Request Contract: InvocationRequest

```python
class InvocationRequest(BaseModel):
    # Required Fields
    session_id: str           # Session identifier
    request_id: str           # Unique request ID (UUID)
    task_type: str            # Task type identifier
    payload: dict             # Task-specific input
    timestamp: datetime       # Request creation time (ISO 8601)
    trace_id: str             # Distributed tracing ID (UUID)
    
    # Optional Fields
    privacy_level: Optional[Literal["local", "cloud", "auto"]]
    
    # Configuration
    class Config:
        extra = "forbid"      # Reject undeclared fields
```

**Validation Rules:**
- All UUIDs validated as valid UUID format
- Max payload size: 1MB (recommended)
- timestamp must be ISO 8601 format

---

### Response Contract: InvocationResponse

#### Success Response
```python
class InvocationResponse(BaseModel):
    # Echo from request
    session_id: str
    request_id: str
    trace_id: str
    
    # Execution results
    status: Literal["success"]
    result: dict
    error: None
    
    # Metadata
    timestamp: datetime       # Response generation time
    execution_time_ms: float  # Execution duration
```

#### Error Response
```python
class InvocationResponse(BaseModel):
    # Echo from request
    session_id: str
    request_id: str
    trace_id: str
    
    # Error details
    status: str               # Error category (e.g., "validation_error")
    result: dict              # Empty dict
    error: ErrorDetail        # Structured error object
    
    # Metadata
    timestamp: datetime
    execution_time_ms: float

class ErrorDetail(BaseModel):
    code: str                 # E-EXEC-001, E-EXEC-002, etc.
    message: str              # Human-readable message
    recoverable: bool         # Whether retry might succeed
```

**Error Codes:**
- `E-EXEC-001` — UnsupportedTask
- `E-EXEC-002` — ValidationError
- `E-EXEC-003` — ExecutionTimeout
- `E-EXEC-004` — PrivacyViolation
- `E-EXEC-005` — PayloadTooLarge

---

### Logging Contract

#### Required Events

**1. invocation_started**
```json
{
  "event_name": "invocation_started",
  "timestamp": "2026-02-20T10:00:00.000Z",
  "trace_id": "uuid",
  "session_id": "uuid",
  "request_id": "uuid",
  "task_type": "echo"
}
```

**2. invocation_executed**
```json
{
  "event_name": "invocation_executed",
  "timestamp": "2026-02-20T10:00:00.050Z",
  "trace_id": "uuid",
  "session_id": "uuid",
  "request_id": "uuid",
  "task_type": "echo",
  "status": "success",
  "latency_ms": 50.0
}
```

**3. invocation_completed**
```json
{
  "event_name": "invocation_completed",
  "timestamp": "2026-02-20T10:00:00.051Z",
  "trace_id": "uuid",
  "session_id": "uuid",
  "request_id": "uuid",
  "status": "success"
}
```

**4. error_raised**
```json
{
  "event_name": "error_raised",
  "timestamp": "2026-02-20T10:00:00.020Z",
  "trace_id": "uuid",
  "session_id": "uuid",
  "request_id": "uuid",
  "task_type": "unsupported",
  "error_code": "E-EXEC-001",
  "error_message": "Unsupported task type: unsupported",
  "recoverable": false
}
```

#### Redaction Policy

**Production (Default):**
- ❌ MUST NOT log payload content (raw data)
- ✅ MAY log `payload_size_bytes` or `payload_hash`
- ❌ MUST NOT log session_id in plain text (hash or truncate)

**Development (Explicit Enable Only):**
- ✅ MAY log payload if `LOG_PAYLOAD_CONTENT=true`
- ✅ MAY log full session_id

---

## Mandatory Non-Functional Requirements

### 1. Determinism
- **Rule:** Same input → same output, always
- **Test:** Unit tests with snapshot testing
- **Violation:** Randomness, timestamps in business logic

### 2. Traceability
- **Rule:** Every invocation reconstructible from logs
- **Test:** Given trace_id, retrieve full execution path
- **Violation:** Missing trace_id, missing log events

### 3. Fail-Fast
- **Rule:** Errors returned immediately without retry
- **Test:** Error tests verify immediate return
- **Violation:** Retry logic, silent catch blocks

### 4. Single Invocation Scope
- **Rule:** One request → one response, no chaining
- **Test:** Integration tests verify single response
- **Violation:** Recursive calls, background tasks

### 5. Statelessness
- **Rule:** No state persists between invocations
- **Test:** Multiple identical requests produce identical results
- **Violation:** In-memory caching, session storage

### 6. Observability
- **Rule:** All events logged with structured fields
- **Test:** Log output conforms to observability-standard.md
- **Violation:** Missing events, unstructured logs

### 7. Error Doctrine Compliance
- **Rule:** All errors structured with code, message, trace_id, recoverable
- **Test:** Error tests verify structured format
- **Violation:** Raw string errors, missing fields

### 8. Privacy Enforcement (Guard Rail)
- **Rule:** If privacy_level == "local", block network tasks
- **Test:** Network tasks rejected when privacy_level == "local"
- **Violation:** Network calls despite privacy constraint

### 9. Schema Validation
- **Rule:** Reject requests with undeclared fields
- **Test:** Pydantic validation with `extra = "forbid"`
- **Violation:** Accepting invalid requests

### 10. Performance
- **Rule:** Execution timing captured and reported
- **Test:** Response includes execution_time_ms
- **Violation:** No timing instrumentation

---

## Compliance Gates

### Gate 1: Architectural Purity
- [ ] No routing logic exists
- [ ] No session management exists
- [ ] No persistence layer exists
- [ ] No autonomous behavior exists
- [ ] Stateless execution maintained
- [ ] Single invocation boundary respected

**Status:** ✅ PASS (current implementation)

### Gate 2: Observability Compliance
- [ ] Structured logging implemented
- [ ] All required events emitted
- [ ] All required fields present
- [ ] trace_id propagated end-to-end
- [ ] Logs conform to observability-standard.md

**Status:** ❌ FAIL (must implement)

### Gate 3: Error Doctrine Compliance
- [ ] Structured error codes defined
- [ ] All errors include code, message, trace_id, recoverable
- [ ] Errors logged before return
- [ ] No silent failures

**Status:** ❌ FAIL (must implement)

### Gate 4: Schema Compliance
- [ ] All required fields present in InvocationRequest
- [ ] All required fields present in InvocationResponse
- [ ] Pydantic `extra = "forbid"` configured
- [ ] Payload size limits enforced

**Status:** ❌ FAIL (must implement)

---

## Enforcement

### Pre-Merge Checklist

Before merging any code:
1. ✅ Zero architectural violations (Gates 1)
2. ✅ All observability requirements met (Gate 2)
3. ✅ All error doctrine requirements met (Gate 3)
4. ✅ All schema requirements met (Gate 4)
5. ✅ Unit tests cover all paths
6. ✅ Integration tests validate contracts
7. ✅ Manual testing confirms compliance

### Continuous Validation

Runtime checks:
- [ ] All invocations emit required log events
- [ ] All errors include structured format
- [ ] All responses include timing
- [ ] No undeclared state mutations
- [ ] No network calls when privacy_level == "local"

### Audit Trail

Every production invocation must be auditable:
- Given trace_id → retrieve full execution log
- Given session_id → retrieve all related invocations
- Given error_code → understand failure mode

---

## Contract Versioning

**Current Version:** 2.0

**Changes from 1.0 (X-2):**
- Added observability requirements (trace_id, logging)
- Added error doctrine requirements (structured errors)
- Added privacy enforcement (guard rail)
- Added timing instrumentation
- Added schema validation requirements

**Breaking Changes:**
- InvocationRequest now requires additional fields
- InvocationResponse now requires additional fields
- Error format changed from string to structured object

**Migration Path:**
- Phase 2A implements all new requirements
- Backward compatibility NOT guaranteed (X-2 → 2.0 is breaking change)

---

## Governance

This contract is derived from:
- `context-index.md` — Core schemas
- `error-doctrine.md` — Error handling rules
- `error-handling.md` — Error policy
- `invocation-boundary.md` — Execution scope
- `memory-lifecycle.md` — Session rules
- `observability-standard.md` — Logging requirements
- `router-decision-matrix.md` — Routing prohibition
- `security-model.md` — Privacy enforcement
- `session-management.md` — Session boundaries
- `evaluation-framework.md` — Testing requirements
- `mvp-consistency-checklist.md` — Compliance gates

**Any deviation from this contract requires:**
1. Explicit documentation in ADR
2. Update to this contract version
3. Re-validation against design specifications

---

## Summary

### ✅ Allowed
- Execute deterministic tasks
- Log structured events
- Echo traceability identifiers
- Enforce privacy (guard rail)
- Return structured errors
- Fail fast

### ❌ Forbidden
- Routing decisions
- Session management
- Persistence
- Autonomous behavior
- Recursive invocation
- Silent failure
- Configuration mutation

### 📋 Mandatory
- Structured logging (JSON)
- Error codes (E-EXEC-*)
- Timing instrumentation
- trace_id propagation
- Schema validation (`extra = "forbid"`)
- Privacy enforcement (if privacy_level == "local")

---

**Contract Status:** ✅ Defined and Ready for Enforcement  
**Next Phase:** Implement compliance requirements (Phase 2A)

