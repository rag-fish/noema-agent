# Design Re-Validation — Strict Compliance Check

**Date:** February 20, 2026  
**Status:** Phase 1 — Design Constraint Extraction Complete  
**Purpose:** Extract exact constraints from RAGfish design specifications and validate noema-agent compliance

---

## STEP 1 — Design Re-Validation

### Design File: `context-index.md`

#### Quoted Constraint 1:
> "No hidden autonomous execution"

**Derived Rule for noema-agent:**
- MUST NOT execute any task without explicit invocation request
- MUST NOT schedule background tasks
- MUST NOT pre-fetch or pre-compute responses
- MUST NOT trigger recursive invocations

**Current Implementation Compliant?** ✅ **YES**
- Reason: `/invoke` endpoint only executes on explicit POST request
- No background workers or scheduled tasks exist
- No autonomous behavior detected

#### Quoted Constraint 2:
> "No implicit routing escalation"

**Derived Rule for noema-agent:**
- MUST NOT make routing decisions (local vs cloud)
- MUST NOT escalate to alternative execution paths without explicit instruction
- MUST NOT contain fallback logic

**Current Implementation Compliant?** ✅ **YES**
- Reason: No routing logic exists in codebase
- Executor only processes predetermined task_type
- No escalation or fallback paths present

#### Quoted Constraint 3:
> "All model invocation must respect invocation boundary"

**Derived Rule for noema-agent:**
- MUST have single entry point per invocation
- MUST have single exit point per invocation
- MUST NOT chain multiple invocations
- MUST produce exactly one response per request

**Current Implementation Compliant?** ✅ **YES**
- Reason: `/invoke` endpoint is single entry point
- `execute_task()` returns exactly one InvocationResponse
- No chaining detected

#### Quoted Constraint 4:
> "NoemaQuestion Required fields: id (UUID), session_id (UUID), content (string), privacy_level (enum), timestamp (ISO-8601)"

**Derived Rule for noema-agent:**
- MUST accept `session_id` in request
- SHOULD accept `request_id` or `question_id` for traceability
- SHOULD accept `timestamp` for logging
- SHOULD accept `privacy_level` for enforcement

**Current Implementation Compliant?** ⚠️ **PARTIAL**
- Reason: Current InvocationRequest has `session_id` ✅
- Missing: `request_id`, `timestamp`, `privacy_level` fields ⚠️
- Impact: Reduced traceability and observability

---

### Design File: `error-doctrine.md`

#### Quoted Constraint 1:
> "All errors must belong to a typed category" (E-ROUTE-001, E-LOCAL-001, E-VALID-001, E-SESSION-001, etc.)

**Derived Rule for noema-agent:**
- MUST use structured error codes (E-EXEC-001, E-EXEC-002, etc.)
- MUST NOT return raw string errors
- MUST categorize all error types

**Current Implementation Compliant?** ❌ **NO**
- Reason: Current error is simple string `"unsupported_task"`
- No error codes like `E-EXEC-001` defined
- Status field uses `"error"` instead of specific error category
- Impact: Non-compliant with error doctrine

#### Quoted Constraint 2:
> "Structured Error Response: { status: 'error', error_code: 'E-LOCAL-001', message: '...', recoverable: false, session_id: 'uuid', question_id: 'uuid', timestamp: 'ISO8601' }"

**Derived Rule for noema-agent:**
- MUST include `error_code` field
- MUST include `recoverable` boolean
- MUST include `timestamp` in errors
- MUST include `question_id` or `request_id`

**Current Implementation Compliant?** ❌ **NO**
- Reason: Error response missing required fields:
  - `error_code` ❌
  - `recoverable` ❌
  - `timestamp` ❌
  - `request_id` ❌
- Impact: Critical non-compliance with error doctrine

#### Quoted Constraint 3:
> "Fail-Fast Policy: The system must terminate execution immediately when an error occurs. No silent retry."

**Derived Rule for noema-agent:**
- MUST return error immediately without retry
- MUST NOT catch and suppress exceptions silently
- MUST log all errors before returning

**Current Implementation Compliant?** ⚠️ **PARTIAL**
- Reason: Executor returns error immediately ✅
- No retry logic present ✅
- But: No logging of errors ⚠️
- Impact: Observability gap

#### Quoted Constraint 4:
> "No Autonomous Recovery Rule: The system must never attempt self-correction without human intervention."

**Derived Rule for noema-agent:**
- MUST NOT automatically retry failed tasks
- MUST NOT attempt alternative execution strategies
- MUST NOT modify request to "fix" errors

**Current Implementation Compliant?** ✅ **YES**
- Reason: No autonomous recovery logic exists
- Errors returned as-is without modification

---

### Design File: `error-handling.md`

#### Quoted Constraint 1:
> "No Silent Failure: Every failure must be Logged, Classified, Traceable via trace-id"

**Derived Rule for noema-agent:**
- MUST log every error with trace_id
- MUST classify error by category
- MUST ensure traceability

**Current Implementation Compliant?** ❌ **NO**
- Reason: No logging implemented
- No trace_id in request or response
- Errors not classified by category
- Impact: Critical observability violation

#### Quoted Constraint 2:
> "Deterministic Failure Response: Given the same input and same system state, the same error must be produced."

**Derived Rule for noema-agent:**
- MUST produce identical errors for identical inputs
- MUST NOT introduce randomness in error generation

**Current Implementation Compliant?** ✅ **YES**
- Reason: Error logic is deterministic (simple if/else)
- Same input produces same error

#### Quoted Constraint 3:
> "Structured Error Response Format: { error: { code: 'ROUTING_ERROR', message: '...', trace_id: 'uuid', timestamp: 'ISO-8601' } }"

**Derived Rule for noema-agent:**
- MUST use nested error object with code, message, trace_id, timestamp
- OR: Flatten these fields at top level if consistent with spec

**Current Implementation Compliant?** ❌ **NO**
- Reason: Missing `code`, `trace_id`, `timestamp`
- Error is simple string, not structured object

#### Quoted Constraint 4:
> "Retry Policy: Retries allowed only for network timeout, max 1 retry, must be logged"

**Derived Rule for noema-agent:**
- MUST NOT retry execution errors
- IF implementing network calls: follow strict retry policy
- Currently: No retry needed (no network calls)

**Current Implementation Compliant?** ✅ **YES**
- Reason: No retry logic exists (correct for current scope)

---

### Design File: `execution-flow.md`

*(Already analyzed in previous documents - key points:)*

#### Quoted Constraint:
> "Step 5 — Execution Path: Execution is synchronous. No background autonomy, no recursive self-calls."

**Derived Rule for noema-agent:**
- MUST execute synchronously
- MUST NOT spawn background tasks
- MUST NOT call itself recursively

**Current Implementation Compliant?** ✅ **YES**
- Reason: FastAPI endpoint executes synchronously
- No background workers or async tasks
- No recursive calls

---

### Design File: `invocation-boundary.md`

#### Quoted Constraint 1:
> "An Invocation MUST: Be traceable, Be logged, Respect privacy_level, Respect Router decision"

**Derived Rule for noema-agent:**
- MUST log every invocation with trace_id
- MUST respect privacy_level (if present)
- MUST be traceable end-to-end

**Current Implementation Compliant?** ❌ **NO**
- Reason: No logging implemented ❌
- No privacy_level handling ❌
- No trace_id ❌
- Impact: Critical compliance violation

#### Quoted Constraint 2:
> "Each Invocation MUST record: question_id, routing_decision, selected_model, execution_result, fallback_usage, execution_timestamp"

**Derived Rule for noema-agent:**
- MUST log all required fields
- Note: noema-agent doesn't make routing decisions (correct)
- MUST log: request_id, task_type, status, timestamp

**Current Implementation Compliant?** ❌ **NO**
- Reason: No logging infrastructure present
- Impact: Cannot audit executions

#### Quoted Constraint 3:
> "Invocation Lifecycle: Human Action → Question Object Created → Router Decision → Execution → Response Object Generated → Return to Human. Execution ends here."

**Derived Rule for noema-agent:**
- MUST NOT continue execution beyond response generation
- MUST NOT trigger follow-up actions
- MUST return control to caller

**Current Implementation Compliant?** ✅ **YES**
- Reason: Endpoint returns response and exits
- No continuation logic

#### Quoted Constraint 4:
> "During an Invocation, the system MUST NOT: Modify system configuration, Persist memory outside declared path, Escalate routing silently, Execute undeclared external calls"

**Derived Rule for noema-agent:**
- MUST NOT modify configuration
- MUST NOT persist state
- MUST NOT make undeclared calls
- MUST NOT escalate routing

**Current Implementation Compliant?** ✅ **YES**
- Reason: No configuration mutation
- No persistence layer
- No external calls
- No routing logic

---

### Design File: `memory-lifecycle.md`

#### Quoted Constraint 1:
> "Memory is strictly session-scoped. There is no cross-session persistence. Session Timeout: 45 minutes (fixed)."

**Derived Rule for noema-agent:**
- MUST NOT store session data
- MUST NOT enforce 45-minute timeout (client responsibility)
- MUST only echo session_id for traceability

**Current Implementation Compliant?** ✅ **YES**
- Reason: No session storage exists
- session_id is echoed but not stored
- No timeout enforcement (correct)

#### Quoted Constraint 2:
> "Server may hold session data during active session only. Server must discard all session data upon timeout expiration or explicit termination."

**Derived Rule for noema-agent:**
- IF storing ephemeral session data (future): MUST delete on timeout
- Currently: No storage, so N/A

**Current Implementation Compliant?** ✅ **YES**
- Reason: No session storage, fully stateless

#### Quoted Constraint 3:
> "Forbidden Behaviors: Automatic long-term summarization for retention, Silent memory compression, Cross-session carry-over"

**Derived Rule for noema-agent:**
- MUST NOT store memory across invocations
- MUST NOT compress or summarize session data
- MUST NOT correlate sessions

**Current Implementation Compliant?** ✅ **YES**
- Reason: Completely stateless, no memory operations

---

### Design File: `router-decision-matrix.md`

*(Already analyzed - confirming key point:)*

#### Quoted Constraint:
> "The Router MUST execute client-side. The server MUST NOT make routing decisions."

**Derived Rule for noema-agent:**
- MUST NOT contain routing logic
- MUST NOT decide local vs cloud
- MUST NOT select models
- MUST NOT perform fallback routing

**Current Implementation Compliant?** ✅ **YES**
- Reason: Zero routing logic in codebase
- No model selection
- No fallback logic

---

### Design File: `security-model.md`

#### Quoted Constraint 1:
> "privacy_level == local must guarantee zero network transmission of content. Router must log the privacy decision."

**Derived Rule for noema-agent:**
- IF privacy_level == "local": MUST block network-dependent tasks
- MUST log privacy enforcement decisions
- Note: Guard rail, not routing decision

**Current Implementation Compliant?** ⚠️ **PARTIAL**
- Reason: No privacy_level field in request ❌
- No network calls exist (so no violation currently) ✅
- No logging of privacy decisions ❌
- Impact: Cannot enforce privacy if needed

#### Quoted Constraint 2:
> "Session Protection: Session timeout = 45 minutes (fixed). Server must delete mirrored session data on expiry. Reject reuse of expired session_id."

**Derived Rule for noema-agent:**
- MUST NOT store session data (already compliant)
- IF storing: MUST delete on timeout
- Currently: N/A (no session storage)

**Current Implementation Compliant?** ✅ **YES**
- Reason: No session storage

#### Quoted Constraint 3:
> "Execution Restrictions: No background execution, No recursive invocation, No tool self-discovery, No undeclared external calls"

**Derived Rule for noema-agent:**
- MUST NOT execute in background
- MUST NOT recurse
- MUST NOT discover tools dynamically
- MUST NOT make undeclared calls

**Current Implementation Compliant?** ✅ **YES**
- Reason: All restrictions respected

#### Quoted Constraint 4:
> "Input Validation: All inputs must validate against NoemaQuestion schema. Reject additionalProperties. Enforce maximum input length."

**Derived Rule for noema-agent:**
- MUST validate request schema (Pydantic does this)
- SHOULD enforce max payload size
- SHOULD reject unknown fields

**Current Implementation Compliant?** ⚠️ **PARTIAL**
- Reason: Pydantic validates schema ✅
- No max payload size enforcement ⚠️
- Pydantic accepts additional fields by default ⚠️

---

### Design File: `session-management.md`

#### Quoted Constraint:
> "Client is the primary authority for session state. Server MAY keep an ephemeral mirror... Server MUST treat session_id as a secret."

**Derived Rule for noema-agent:**
- MUST echo session_id in response
- MUST NOT log session_id in plain text (production)
- MUST treat as sensitive identifier
- MUST NOT store or validate session lifecycle

**Current Implementation Compliant?** ⚠️ **PARTIAL**
- Reason: session_id echoed correctly ✅
- No logging yet (so no plain text exposure) ✅
- When logging added: MUST redact or hash ⚠️

---

### Design File: `observability-standard.md`

#### Quoted Constraint 1:
> "All telemetry MUST include: trace_id (UUID), session_id (UUID), question_id (UUID), response_id (UUID). trace_id MUST be generated at Invocation entry."

**Derived Rule for noema-agent:**
- MUST accept trace_id (or generate if missing)
- MUST accept request_id or question_id
- MUST include these in all logs
- MUST echo in response

**Current Implementation Compliant?** ❌ **NO**
- Reason: No trace_id field ❌
- No request_id/question_id field ❌
- No logging infrastructure ❌
- Impact: Critical observability violation

#### Quoted Constraint 2:
> "Required event types: invocation_started, invocation_routed, invocation_executed, invocation_completed, error_raised"

**Derived Rule for noema-agent:**
- MUST emit `invocation_started` event
- MUST emit `invocation_executed` event (with latency_ms)
- MUST emit `invocation_completed` or `error_raised`
- Note: `invocation_routed` N/A (no routing in noema-agent)

**Current Implementation Compliant?** ❌ **NO**
- Reason: No event logging exists
- Impact: Critical observability gap

#### Quoted Constraint 3:
> "Minimum Structured Log Fields: event_name, timestamp (ISO 8601), trace_id, session_id, question_id"

**Derived Rule for noema-agent:**
- MUST log with structured JSON format
- MUST include all required fields
- MUST use ISO 8601 timestamps

**Current Implementation Compliant?** ❌ **NO**
- Reason: No structured logging implemented
- Impact: Critical compliance violation

#### Quoted Constraint 4:
> "Prompt and Data Redaction Policy: Production logs MUST NOT include raw content by default. Allowed: content_hash, content_length, truncated_preview (disabled by default)."

**Derived Rule for noema-agent:**
- MUST NOT log payload content in production
- MAY log content_hash or content_length
- MUST have environment-based redaction

**Current Implementation Compliant?** ⚠️ **N/A (no logging yet)**
- Reason: When logging implemented, MUST follow redaction policy

#### Quoted Constraint 5:
> "invocation_executed event MUST include: route, selected_model, latency_ms, result (success | error)"

**Derived Rule for noema-agent:**
- MUST capture execution start time
- MUST calculate latency_ms
- MUST log result status
- Note: route/model come from upstream (not noema-agent's decision)

**Current Implementation Compliant?** ❌ **NO**
- Reason: No timing instrumentation
- No logging infrastructure

---

### Design File: `evaluation-framework.md`

#### Quoted Constraint 1:
> "L1 — Schema Compliance: Validate that all Question objects conform to NoemaQuestion schema. No undeclared fields are present. privacy_level is honored."

**Derived Rule for noema-agent:**
- MUST validate request schema (Pydantic)
- MUST reject undeclared fields
- MUST honor privacy_level (if present)

**Current Implementation Compliant?** ⚠️ **PARTIAL**
- Reason: Pydantic validates schema ✅
- But: Schema incomplete (missing fields) ⚠️
- privacy_level not implemented ❌

#### Quoted Constraint 2:
> "L3 — Execution Integrity: Each Invocation has exactly one entry point, exactly one exit point, produces one structured Response or one structured Error, does not trigger recursive invocation, does not mutate undeclared state."

**Derived Rule for noema-agent:**
- MUST have single entry point (/invoke)
- MUST have single exit point (return response)
- MUST produce exactly one response
- MUST NOT recurse
- MUST NOT mutate state

**Current Implementation Compliant?** ✅ **YES**
- Reason: All conditions met

#### Quoted Constraint 3:
> "Deterministic Test Mode: Model calls may be mocked, Router decisions are snapshot-testable, Session behavior is time-controlled, Error paths are reproducible."

**Derived Rule for noema-agent:**
- MUST support deterministic testing
- MUST allow mocking of task implementations
- MUST produce reproducible errors

**Current Implementation Compliant?** ✅ **YES**
- Reason: Pure functions, easily testable
- No hidden state or randomness

---

### Design File: `mvp-consistency-checklist.md`

#### Quoted Constraint 1:
> "Human Sovereignty Validation: The user explicitly triggers every execution (no background auto-run). No autonomous task scheduling exists."

**Derived Rule for noema-agent:**
- MUST only execute on explicit request
- MUST NOT schedule tasks
- MUST NOT pre-compute

**Current Implementation Compliant?** ✅ **YES**
- Reason: Explicit endpoint invocation only

#### Quoted Constraint 2:
> "Invocation Boundary Validation: Every LLM invocation is explicit and logged. Invocation metadata includes: session-id, route-type, timestamp. No silent retry logic."

**Derived Rule for noema-agent:**
- MUST log every execution
- MUST include session_id, task_type, timestamp
- MUST NOT retry silently

**Current Implementation Compliant?** ❌ **NO**
- Reason: No logging ❌
- No timestamps ❌
- No retry logic ✅

#### Quoted Constraint 3:
> "Error Handling Compliance: All errors return structured response (code, message, trace-id). No silent failure paths."

**Derived Rule for noema-agent:**
- MUST use structured errors with code, message, trace_id
- MUST NOT suppress errors

**Current Implementation Compliant?** ❌ **NO**
- Reason: Errors lack code and trace_id
- Impact: Non-compliant with checklist gate

#### Quoted Constraint 4:
> "Observability & Auditability: Each execution produces structured logs. Logs include routing decision (N/A for noema-agent), invocation boundary confirmation."

**Derived Rule for noema-agent:**
- MUST produce structured logs
- MUST log invocation boundary events
- MUST enable reconstruction of execution

**Current Implementation Compliant?** ❌ **NO**
- Reason: No logging infrastructure

---

## STEP 2 — Codebase Compliance Check

### Analysis of Current noema-agent Implementation

#### File: `app/main.py`

**Routing Logic Check:**
- ❌ No routing logic detected ✅ COMPLIANT
- ❌ No model selection detected ✅ COMPLIANT
- ❌ No fallback logic detected ✅ COMPLIANT

**Session State Mutation Check:**
- ❌ No session storage detected ✅ COMPLIANT
- ❌ No state persistence detected ✅ COMPLIANT
- ✅ session_id echoed correctly ✅ COMPLIANT

**Autonomous Decisions Check:**
- ❌ No background workers ✅ COMPLIANT
- ❌ No scheduled tasks ✅ COMPLIANT
- ❌ No recursive calls ✅ COMPLIANT

**Observability Check:**
- ❌ No logging infrastructure ❌ NON-COMPLIANT
- ❌ No timing instrumentation ❌ NON-COMPLIANT
- ❌ No structured events ❌ NON-COMPLIANT

**Error Handling Check:**
- ⚠️ Errors returned but not structured per doctrine ❌ NON-COMPLIANT
- ⚠️ No error codes ❌ NON-COMPLIANT
- ⚠️ No trace_id ❌ NON-COMPLIANT

#### File: `app/models.py`

**Schema Compliance Check:**
- ✅ InvocationRequest has session_id ✅ COMPLIANT
- ✅ InvocationRequest has task_type ✅ COMPLIANT
- ✅ InvocationRequest has payload ✅ COMPLIANT
- ❌ Missing request_id/question_id ❌ NON-COMPLIANT
- ❌ Missing timestamp ❌ NON-COMPLIANT
- ❌ Missing trace_id ❌ NON-COMPLIANT
- ❌ Missing privacy_level ❌ NON-COMPLIANT

**Error Response Compliance Check:**
- ✅ InvocationResponse has session_id ✅ COMPLIANT
- ✅ InvocationResponse has status ✅ COMPLIANT
- ✅ InvocationResponse has result ✅ COMPLIANT
- ✅ InvocationResponse has error ✅ COMPLIANT
- ❌ Missing error_code ❌ NON-COMPLIANT
- ❌ Missing recoverable flag ❌ NON-COMPLIANT
- ❌ Missing timestamp ❌ NON-COMPLIANT
- ❌ Missing trace_id ❌ NON-COMPLIANT
- ❌ Missing request_id echo ❌ NON-COMPLIANT
- ❌ Missing execution_time_ms ❌ NON-COMPLIANT

**Pydantic Configuration Check:**
- ⚠️ No `extra = "forbid"` to reject undeclared fields ⚠️ GREY AREA
- ⚠️ No payload size validation ⚠️ GREY AREA

#### File: `app/executor.py`

**Execution Integrity Check:**
- ✅ Single entry point (execute_task) ✅ COMPLIANT
- ✅ Single exit point (return statement) ✅ COMPLIANT
- ✅ Deterministic behavior ✅ COMPLIANT
- ✅ No state mutation ✅ COMPLIANT
- ✅ No recursion ✅ COMPLIANT

**Error Handling Check:**
- ⚠️ Error returned but not logged ❌ NON-COMPLIANT
- ⚠️ Error lacks structured format (code, trace_id) ❌ NON-COMPLIANT
- ⚠️ No timing instrumentation ❌ NON-COMPLIANT

**Privacy Enforcement Check:**
- ❌ No privacy_level validation ❌ NON-COMPLIANT (but also not yet required)

**Logging Check:**
- ❌ No invocation_started event ❌ NON-COMPLIANT
- ❌ No invocation_executed event ❌ NON-COMPLIANT
- ❌ No error_raised event ❌ NON-COMPLIANT

---

### Compliance Summary

#### ✅ ZERO ARCHITECTURAL VIOLATIONS DETECTED

**Core Principles Preserved:**
- No routing logic (correct absence)
- No session state storage (correct absence)
- No autonomous behavior (correct absence)
- No persistence layer (correct absence)
- Single invocation boundary (correct)
- Deterministic execution (correct)

#### ❌ CRITICAL COMPLIANCE GAPS

**Observability Violations:**
1. No structured logging infrastructure
2. No trace_id propagation
3. No event emission (invocation_started, invocation_executed, etc.)
4. No timing instrumentation (latency_ms)
5. No request_id/question_id for traceability

**Error Doctrine Violations:**
6. Errors lack structured error codes (E-EXEC-001, etc.)
7. Errors lack trace_id
8. Errors lack timestamp
9. Errors lack recoverable flag
10. Errors not logged before return

**Schema Compliance Violations:**
11. InvocationRequest missing required observability fields (trace_id, request_id, timestamp)
12. InvocationRequest missing privacy_level for enforcement
13. InvocationResponse missing trace_id echo
14. InvocationResponse missing timestamp
15. InvocationResponse missing execution_time_ms

#### ⚠️ GREY AREAS

1. **Pydantic Configuration:** Should use `extra = "forbid"` to reject undeclared fields (security-model.md requirement)
2. **Payload Size Limits:** No max payload size validation (DoS risk)
3. **Privacy Enforcement:** No privacy_level handling (but no network calls exist, so no immediate violation)

---

## STEP 3 — Guardrail Contract

### Allowed Responsibilities

1. ✅ **Accept Invocation Requests** — Receive structured InvocationRequest via `/invoke` endpoint
2. ✅ **Validate Request Schema** — Use Pydantic to enforce required fields and types
3. ✅ **Execute Deterministic Tasks** — Dispatch to registered task implementations based on task_type
4. ✅ **Generate Structured Responses** — Return InvocationResponse with status, result, or error
5. ✅ **Echo Traceability Identifiers** — Echo session_id, request_id, trace_id in response
6. ✅ **Emit Structured Logs** — Log invocation events with required observability fields
7. ✅ **Measure Execution Timing** — Capture and report execution_time_ms
8. ✅ **Enforce Privacy Constraints** — Block network-dependent tasks if privacy_level == "local" (guard rail, not routing)
9. ✅ **Return Structured Errors** — Use error codes, include trace_id, mark as recoverable/non-recoverable
10. ✅ **Fail Fast** — Return errors immediately without retry or silent recovery

### Forbidden Responsibilities

1. ❌ **Routing Decisions** — MUST NOT decide local vs cloud execution (client-side Router responsibility)
2. ❌ **Model Selection** — MUST NOT choose which model to invoke (upstream orchestrator responsibility)
3. ❌ **Fallback Logic** — MUST NOT escalate to alternative execution strategies (Router handles fallback)
4. ❌ **Session Management** — MUST NOT create, validate, or enforce 45-minute session timeout (client responsibility)
5. ❌ **Session Memory Storage** — MUST NOT store conversation history or session state (stateless executor)
6. ❌ **Persistence** — MUST NOT write to database or filesystem (except logs)
7. ❌ **Background Execution** — MUST NOT schedule tasks, spawn workers, or pre-compute responses
8. ❌ **Recursive Invocation** — MUST NOT call itself or trigger chained invocations
9. ❌ **Autonomous Recovery** — MUST NOT retry failed tasks or modify requests to "fix" errors
10. ❌ **Tool Discovery** — MUST NOT dynamically discover or register tools at runtime
11. ❌ **Silent Failure** — MUST NOT suppress errors or hide execution failures
12. ❌ **Configuration Mutation** — MUST NOT modify system configuration during execution
13. ❌ **Prompt Rewriting** — MUST NOT modify user input or task payload
14. ❌ **Cross-Session Correlation** — MUST NOT link or analyze data across sessions

### Mandatory Interface Requirements

#### Request Contract (InvocationRequest)

**Required Fields:**
- `session_id: str` — Session identifier for correlation
- `request_id: str` — Unique request identifier (UUID) for traceability
- `task_type: str` — Task type identifier (e.g., "echo", "transform")
- `payload: dict` — Task-specific input data
- `timestamp: datetime` — Request creation time (ISO 8601)
- `trace_id: str` — Distributed tracing identifier (UUID)

**Optional Fields:**
- `privacy_level: Literal["local", "cloud", "auto"]` — Privacy constraint from upstream

**Validation Rules:**
- Pydantic `extra = "forbid"` to reject undeclared fields
- Max payload size limit (recommended: 1MB)
- All UUIDs validated as valid UUID format

#### Response Contract (InvocationResponse)

**Required Fields (Success):**
- `session_id: str` — Echo from request
- `request_id: str` — Echo from request
- `trace_id: str` — Echo from request
- `status: str` — Execution status ("success")
- `result: dict` — Task-specific output data
- `error: None` — Null for success
- `timestamp: datetime` — Response generation time (ISO 8601)
- `execution_time_ms: float` — Execution duration in milliseconds

**Required Fields (Error):**
- `session_id: str` — Echo from request
- `request_id: str` — Echo from request
- `trace_id: str` — Echo from request
- `status: str` — Error category (e.g., "validation_error", "execution_error")
- `result: dict` — Empty dict
- `error: dict` — Structured error object:
  - `code: str` — Error code (e.g., "E-EXEC-001")
  - `message: str` — Human-readable error message
  - `recoverable: bool` — Whether retry might succeed
- `timestamp: datetime` — Error timestamp (ISO 8601)
- `execution_time_ms: float` — Time until failure

#### Logging Contract

**Required Events:**
1. `invocation_started` — Log on entry to execute_task()
2. `invocation_executed` — Log on successful task completion
3. `invocation_completed` — Log before returning response
4. `error_raised` — Log on any error

**Required Log Fields (All Events):**
- `event_name: str`
- `timestamp: str` (ISO 8601)
- `trace_id: str`
- `session_id: str`
- `request_id: str`
- `task_type: str`

**Additional Fields (invocation_executed):**
- `status: str` ("success" | error category)
- `latency_ms: float`

**Additional Fields (error_raised):**
- `error_code: str`
- `error_message: str`
- `recoverable: bool`

**Redaction Policy:**
- Production: MUST NOT log payload content (raw data)
- Production: MAY log payload_size_bytes or payload_hash
- Development: MAY log payload if explicitly enabled via env var

### Mandatory Non-Functional Requirements

#### 1. Determinism
- **Requirement:** Same input → same output, always
- **Validation:** Unit tests with snapshot testing
- **Violation:** Any randomness, timestamps in business logic, or probabilistic behavior

#### 2. Traceability
- **Requirement:** Every invocation fully reconstructible from logs
- **Validation:** Given trace_id, can retrieve full execution path
- **Violation:** Missing trace_id, missing log events, incomplete error details

#### 3. Fail-Fast
- **Requirement:** Errors returned immediately without retry
- **Validation:** Error tests verify immediate return
- **Violation:** Retry logic, silent catch blocks, error suppression

#### 4. Single Invocation Scope
- **Requirement:** One request → one response, no chaining
- **Validation:** Integration tests verify single response per request
- **Violation:** Recursive calls, background tasks, follow-up invocations

#### 5. Statelessness
- **Requirement:** No state persists between invocations
- **Validation:** Multiple identical requests produce identical results
- **Violation:** In-memory caching, session storage, filesystem writes

#### 6. Observability
- **Requirement:** All execution events logged with structured fields
- **Validation:** Log output conforms to observability-standard.md
- **Violation:** Missing log events, unstructured logs, missing required fields

#### 7. Error Doctrine Compliance
- **Requirement:** All errors structured with code, message, trace_id, recoverable flag
- **Validation:** Error tests verify structured error format
- **Violation:** Raw string errors, missing error codes, missing trace_id

#### 8. Privacy Enforcement (Guard Rail)
- **Requirement:** If privacy_level == "local", block network-dependent tasks
- **Validation:** Test that network tasks rejected when privacy_level == "local"
- **Violation:** Network calls when privacy_level == "local"

#### 9. Schema Validation
- **Requirement:** Reject requests with undeclared fields or invalid types
- **Validation:** Pydantic validation with `extra = "forbid"`
- **Violation:** Accepting invalid requests, lenient schema

#### 10. Performance
- **Requirement:** Execution timing captured and reported
- **Validation:** Response includes execution_time_ms
- **Violation:** No timing instrumentation, inaccurate measurements

---

## Compliance Gate Summary

### ✅ Architectural Compliance: PASS

**Zero violations of core architectural principles:**
- No routing logic (correct)
- No session management (correct)
- No persistence (correct)
- No autonomous behavior (correct)
- Stateless execution (correct)
- Single invocation boundary (correct)

### ❌ Observability Compliance: FAIL

**Critical gaps:**
- No structured logging
- No trace_id propagation
- No event emission
- No timing instrumentation

### ❌ Error Doctrine Compliance: FAIL

**Critical gaps:**
- Errors lack structured codes
- Errors lack trace_id
- Errors lack timestamp
- Errors lack recoverable flag
- Errors not logged

### ⚠️ Schema Compliance: PARTIAL

**Gaps:**
- Missing observability fields (trace_id, request_id, timestamp)
- Missing privacy_level field
- Missing Pydantic `extra = "forbid"`

---

## Next Phase Requirements

### Phase 2A: Critical Compliance (Required for MVP)

1. **Add Observability Fields to Models**
   - InvocationRequest: Add request_id, timestamp, trace_id, privacy_level
   - InvocationResponse: Add request_id, timestamp, trace_id, execution_time_ms
   - Add structured error format with error_code, recoverable

2. **Implement Structured Logging**
   - Add logging infrastructure (Python `logging` module with JSON formatter)
   - Emit invocation_started, invocation_executed, invocation_completed, error_raised events
   - Include all required fields per observability-standard.md

3. **Implement Timing Instrumentation**
   - Capture execution start time
   - Calculate execution_time_ms
   - Include in response

4. **Implement Error Codes**
   - Define error code enum (E-EXEC-001: UnsupportedTask, E-EXEC-002: ValidationError, etc.)
   - Update error responses to include code, recoverable, trace_id, timestamp

5. **Add Pydantic Configuration**
   - Set `extra = "forbid"` on models
   - Add max payload size validation

### Phase 2B: Privacy Enforcement (Optional Enhancement)

6. **Implement Privacy Guard Rail**
   - Validate privacy_level in request
   - Block network-dependent tasks if privacy_level == "local"
   - Log privacy enforcement events

---

## Conclusion

**Architectural Integrity:** ✅ **PRESERVED**

The current noema-agent implementation correctly interprets its role as a stateless executor with no routing, session management, or autonomous behavior.

**Compliance Status:** ❌ **NON-COMPLIANT** with observability and error doctrine requirements

**Action Required:** Implement Phase 2A (Critical Compliance) before MVP integration.

**Guardrail Contract:** Defined and ready for validation in next implementation phase.

---

**Status:** ✅ Validation Complete — Implementation Blockers Identified  
**Next Step:** Implement Phase 2A to achieve MVP compliance

