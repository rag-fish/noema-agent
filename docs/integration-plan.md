# Integration Plan — noema-agent with Noesis Noema Architecture

**Date:** February 20, 2026  
**Status:** Design Analysis — No Implementation Yet  
**Version:** 1.0.0

---

## Executive Summary

This document analyzes the RAGfish design specifications and proposes a clean integration plan for **noema-agent** that maintains strict architectural compliance with the Noesis Noema execution layer principles.

**Key Finding:** Current implementation is **architecturally compliant** but requires contract alignment and extension mechanisms.

---

## 1. Architectural Constraints for noema-agent

Based on analysis of:
- `router-decision-matrix.md`
- `invocation-boundary.md`
- `execution-flow.md`
- `security-model.md`
- `session-management.md`

### 1.1 What noema-agent MUST BE

✅ **Stateless Executor**
- No decision-making authority
- No routing logic
- No model selection
- Pure task execution only

✅ **Invocation Boundary Respecting**
- Accept exactly one structured request
- Execute exactly one task
- Return exactly one structured response
- No hidden side effects

✅ **Privacy Enforcing**
- Respect `privacy_level` from upstream
- No unauthorized network calls
- No data leakage across invocations

✅ **Session-Aware but Session-Agnostic**
- Accept `session_id` for traceability
- Echo `session_id` in response
- **MUST NOT** store or manage session state
- **MUST NOT** enforce 45-minute timeout (Client/Orchestrator responsibility)

✅ **Deterministic**
- Same input → same output
- No probabilistic behavior
- No learning or adaptation
- No autonomous execution

### 1.2 What noema-agent MUST NOT DO

❌ **No Routing Logic**
- Router lives in Client layer
- noema-agent receives post-routing requests only
- No local vs cloud decisions

❌ **No Session Management**
- Session creation: Client responsibility
- Session timeout (45 min): Client/Orchestrator responsibility
- Session memory: Client-scoped storage
- noema-agent only echoes `session_id`

❌ **No Persistence**
- No database
- No filesystem writes (except logs)
- No memory across invocations

❌ **No Autonomous Behavior**
- No background execution
- No recursive invocation
- No tool self-discovery
- No implicit continuation

❌ **No Model Selection**
- Model is selected by orchestrator/router
- noema-agent executes with pre-configured or specified model

---

## 2. Invocation Boundary Contract Confirmation

### 2.1 Current Contract (X-2)

```python
class InvocationRequest(BaseModel):
    session_id: str
    task_type: str
    payload: dict

class InvocationResponse(BaseModel):
    session_id: str
    status: str
    result: dict
    error: Optional[str]
```

### 2.2 Required Alignment with Design Specs

The current contract is **fundamentally compliant** but needs enrichment:

#### Required Additions

**InvocationRequest extensions:**
```python
class InvocationRequest(BaseModel):
    session_id: str              # ✅ Already present
    task_type: str                # ✅ Already present
    payload: dict                 # ✅ Already present
    
    # Add for full compliance:
    request_id: str               # ⚠️ Required for traceability (UUID)
    timestamp: datetime           # ⚠️ Required for logging
    privacy_level: Literal["local", "cloud", "auto"]  # ⚠️ Required for privacy enforcement
    trace_id: Optional[str]       # ⚠️ Optional for distributed tracing
```

**InvocationResponse extensions:**
```python
class InvocationResponse(BaseModel):
    session_id: str               # ✅ Already present
    status: str                   # ✅ Already present
    result: dict                  # ✅ Already present
    error: Optional[str]          # ✅ Already present
    
    # Add for full compliance:
    request_id: str               # ⚠️ Echo from request
    executed_at: datetime         # ⚠️ Execution timestamp
    execution_time_ms: float      # ⚠️ Performance metric
```

### 2.3 Status Codes Standardization

Current: `"success"` or `"error"`

**Recommended alignment:**
```python
class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"
    PRIVACY_VIOLATION = "privacy_violation"
    UNSUPPORTED_TASK = "unsupported_task"
    EXECUTION_TIMEOUT = "execution_timeout"
```

---

## 3. Stateless vs Session-Scoped Rules

### 3.1 Session Responsibility Matrix

| Responsibility | Owner | noema-agent Role |
|----------------|-------|------------------|
| Session creation | Client | None — receives `session_id` |
| Session timeout (45 min) | Client + Orchestrator | None — does not enforce |
| Session memory storage | Client (authoritative) | None — stateless |
| Session expiration | Client + Orchestrator | None — does not validate |
| `session_id` echo | noema-agent | **Yes — for traceability** |
| `session_id` validation | Orchestrator (optional) | None — trusts upstream |

### 3.2 Stateless Guarantee

noema-agent **MUST**:
- ✅ Accept `session_id` in request
- ✅ Echo `session_id` in response
- ✅ Log `session_id` for observability

noema-agent **MUST NOT**:
- ❌ Store session state
- ❌ Validate session expiration
- ❌ Manage session memory
- ❌ Cross-reference previous invocations

**Rationale:** Session lifecycle is a Client/Orchestrator concern. The executor is one layer removed from session policy.

---

## 4. Routing and Decision Logic — Explicit Prohibition

### 4.1 Where Routing Lives

**Router Decision Matrix (Section 3):**
> The Router MUST execute client-side.  
> The server MUST NOT make routing decisions.

**Execution Flow (Step 3):**
> Execution Location: Client-side  
> The Router executes entirely within the Client boundary.  
> The server does not make routing decisions.

### 4.2 noema-agent Position in Architecture

```
┌──────────────────────────────────────────┐
│ Client (User Device)                     │
│  ├─ User Input (Noesis)                  │
│  ├─ Session Management (45 min timeout)  │
│  ├─ Router Decision Matrix               │ ← ROUTING HAPPENS HERE
│  └─ Orchestrator / Request Builder       │
└──────────────┬───────────────────────────┘
               │ POST /invoke
               ↓
┌──────────────────────────────────────────┐
│ noema-agent (Execution Layer)            │ ← NO ROUTING HERE
│  ├─ Invocation Boundary Validation       │
│  ├─ Task Execution (deterministic)       │
│  └─ Response Generation                  │
└──────────────────────────────────────────┘
```

### 4.3 Forbidden Operations

noema-agent **MUST NOT**:
- ❌ Decide local vs cloud execution
- ❌ Select models
- ❌ Perform fallback routing
- ❌ Escalate to cloud on local failure
- ❌ Inspect `privacy_level` for routing (only for privacy enforcement)

**Exception:** noema-agent MAY enforce privacy constraints (e.g., block network calls if `privacy_level == "local"`), but this is **enforcement**, not **routing**.

---

## 5. Task Registry Structure

### 5.1 Design Principles

The Task Registry must be:
- **Declarative** — No hidden logic
- **Extensible** — Easy to add new tasks
- **Deterministic** — Pure functions only
- **Validated** — Schema-enforced
- **Auditable** — Logging at registry level

### 5.2 Proposed Structure

```
app/
  tasks/
    __init__.py          # Task registry and dispatcher
    base.py              # Base task interface
    echo.py              # Echo task implementation
    transform.py         # Example: transform task
    validate.py          # Example: validate task
  executor.py            # High-level executor (uses registry)
  models.py              # Invocation contracts
  main.py                # FastAPI application
```

### 5.3 Task Interface (Base Contract)

```python
# app/tasks/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTask(ABC):
    """
    Base interface for all executable tasks.
    
    All tasks must be:
    - Deterministic (same input → same output)
    - Stateless (no cross-invocation state)
    - Pure (no side effects except logging)
    """
    
    @property
    @abstractmethod
    def task_type(self) -> str:
        """Unique task type identifier."""
        pass
    
    @abstractmethod
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the task with given payload.
        
        Args:
            payload: Task-specific input data
            
        Returns:
            Task-specific result data
            
        Raises:
            TaskExecutionError: On execution failure
        """
        pass
    
    def validate_payload(self, payload: Dict[str, Any]) -> None:
        """
        Optional: Validate payload schema.
        
        Raises:
            ValueError: If payload is invalid
        """
        pass
```

### 5.4 Task Registry Implementation

```python
# app/tasks/__init__.py
from typing import Dict, Type
from app.tasks.base import BaseTask
from app.tasks.echo import EchoTask

class TaskRegistry:
    """
    Deterministic task registry.
    
    Maps task_type strings to task implementations.
    No dynamic registration — all tasks declared at initialization.
    """
    
    def __init__(self):
        self._tasks: Dict[str, BaseTask] = {}
        self._register_builtin_tasks()
    
    def _register_builtin_tasks(self):
        """Register all supported tasks."""
        self.register(EchoTask())
        # Future: self.register(TransformTask())
        # Future: self.register(ValidateTask())
    
    def register(self, task: BaseTask):
        """Register a task implementation."""
        self._tasks[task.task_type] = task
    
    def get_task(self, task_type: str) -> BaseTask:
        """
        Retrieve task by type.
        
        Raises:
            KeyError: If task_type is unsupported
        """
        if task_type not in self._tasks:
            raise KeyError(f"Unsupported task type: {task_type}")
        return self._tasks[task_type]
    
    def list_tasks(self) -> list[str]:
        """List all registered task types."""
        return list(self._tasks.keys())

# Global registry instance
registry = TaskRegistry()
```

### 5.5 Example Task Implementation

```python
# app/tasks/echo.py
from typing import Dict, Any
from app.tasks.base import BaseTask

class EchoTask(BaseTask):
    """
    Echo task: returns payload unchanged.
    
    Useful for testing and validation.
    """
    
    @property
    def task_type(self) -> str:
        return "echo"
    
    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Return payload as-is."""
        return payload
```

### 5.6 Executor Integration

```python
# app/executor.py (updated)
from app.models import InvocationRequest, InvocationResponse
from app.tasks import registry
import logging

logger = logging.getLogger(__name__)

def execute_task(request: InvocationRequest) -> InvocationResponse:
    """
    Execute task using registry dispatcher.
    
    Args:
        request: InvocationRequest with task_type and payload
        
    Returns:
        InvocationResponse with status and result
    """
    try:
        # Retrieve task from registry
        task = registry.get_task(request.task_type)
        
        # Validate payload (optional per task)
        task.validate_payload(request.payload)
        
        # Execute task
        result = task.execute(request.payload)
        
        # Return success response
        return InvocationResponse(
            session_id=request.session_id,
            status="success",
            result=result,
            error=None
        )
        
    except KeyError as e:
        # Unsupported task type
        logger.warning(f"Unsupported task: {request.task_type}")
        return InvocationResponse(
            session_id=request.session_id,
            status="unsupported_task",
            result={},
            error=str(e)
        )
        
    except Exception as e:
        # Execution error
        logger.error(f"Task execution failed: {e}", exc_info=True)
        return InvocationResponse(
            session_id=request.session_id,
            status="error",
            result={},
            error=f"Task execution failed: {str(e)}"
        )
```

### 5.7 Registry Benefits

✅ **Separation of Concerns** — Executor delegates to registry  
✅ **Extensibility** — Add tasks without modifying core logic  
✅ **Testability** — Mock individual tasks easily  
✅ **Discoverability** — `registry.list_tasks()` for introspection  
✅ **Type Safety** — Base class enforces contract  

---

## 6. Privacy Enforcement (Not Routing)

### 6.1 Privacy Level Contract

From `security-model.md` and `router-decision-matrix.md`:

> privacy_level == "local" MUST guarantee zero network transmission of content.

### 6.2 noema-agent Responsibility

noema-agent **MAY** enforce privacy constraints as a **guard rail**, not a **router**.

**Example:**
```python
def validate_privacy_constraints(request: InvocationRequest):
    """
    Enforce privacy constraints.
    
    This is NOT routing — routing has already happened.
    This is a safety check to prevent misconfiguration.
    """
    if request.privacy_level == "local":
        # Block any task that requires network access
        if requires_network_access(request.task_type):
            raise PrivacyViolationError(
                "Task requires network access but privacy_level is 'local'"
            )
```

**Key Distinction:**
- ❌ Routing: "Should this go local or cloud?"
- ✅ Enforcement: "This should not have been sent here if privacy_level is X."

---

## 7. Integration Plan Summary

### 7.1 Phase 1: Contract Alignment (No Breaking Changes)

**Goal:** Enrich contracts without breaking X-2 compatibility.

**Actions:**
1. Add optional fields to `InvocationRequest`:
   - `request_id: Optional[str]`
   - `timestamp: Optional[datetime]`
   - `privacy_level: Optional[str]`
   - `trace_id: Optional[str]`

2. Add optional fields to `InvocationResponse`:
   - `request_id: Optional[str]`
   - `executed_at: Optional[datetime]`
   - `execution_time_ms: Optional[float]`

3. Update `/health` endpoint to return `registry.list_tasks()`.

**Result:** Backward-compatible extension.

---

### 7.2 Phase 2: Task Registry Implementation

**Goal:** Replace hardcoded `if task_type == "echo"` with registry pattern.

**Actions:**
1. Create `app/tasks/` package:
   - `base.py` — `BaseTask` interface
   - `echo.py` — `EchoTask` implementation
   - `__init__.py` — `TaskRegistry` class

2. Update `app/executor.py` to use registry.

3. Add unit tests for registry and tasks.

**Result:** Extensible task system.

---

### 7.3 Phase 3: Observability Enhancement

**Goal:** Add structured logging aligned with specs.

**Actions:**
1. Log each invocation:
   - `session_id`
   - `request_id`
   - `task_type`
   - `status`
   - `execution_time_ms`
   - `trace_id` (if present)

2. Add `/metrics` endpoint (optional):
   - Task execution counts
   - Average execution time per task
   - Error rates

**Result:** Production-ready observability.

---

### 7.4 Phase 4: Privacy Enforcement Guards

**Goal:** Add privacy constraint validation (optional).

**Actions:**
1. Add `privacy_level` validation middleware.
2. Block network-dependent tasks if `privacy_level == "local"`.
3. Log privacy enforcement events.

**Result:** Defense-in-depth privacy protection.

---

### 7.5 Phase 5: Error Standardization

**Goal:** Align error responses with design specs.

**Actions:**
1. Define structured error codes:
   - `E-EXEC-001` — Unsupported task
   - `E-EXEC-002` — Validation error
   - `E-EXEC-003` — Execution timeout
   - `E-EXEC-004` — Privacy violation

2. Update `InvocationResponse.error` to use structured format:
   ```python
   {
     "code": "E-EXEC-001",
     "message": "Unsupported task type: xyz",
     "details": {}
   }
   ```

**Result:** Machine-readable error handling.

---

## 8. Architectural Compliance Checklist

### 8.1 Invocation Boundary Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Single entry point (`/invoke`) | ✅ Compliant | Already implemented |
| Single exit point (response) | ✅ Compliant | No hidden continuation |
| No autonomous execution | ✅ Compliant | Human-triggered only |
| Traceability (`session_id`, `request_id`) | ⚠️ Partial | Need `request_id` |
| Logged invocations | ⚠️ Partial | Need structured logging |
| No hidden side effects | ✅ Compliant | Stateless executor |

### 8.2 Stateless Execution Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| No persistence | ✅ Compliant | No database |
| No cross-invocation state | ✅ Compliant | Pure functions |
| Deterministic execution | ✅ Compliant | Same input → same output |
| No learning/adaptation | ✅ Compliant | Static task registry |

### 8.3 Routing Prohibition Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| No local vs cloud decisions | ✅ Compliant | Not implemented |
| No model selection | ✅ Compliant | Not implemented |
| No fallback routing | ✅ Compliant | Not implemented |
| Router lives client-side | ✅ Compliant | Not noema-agent's concern |

### 8.4 Session Management Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Echoes `session_id` | ✅ Compliant | Already implemented |
| No session storage | ✅ Compliant | Stateless |
| No 45-min timeout enforcement | ✅ Compliant | Not implemented (correct) |
| No session memory management | ✅ Compliant | Not implemented (correct) |

### 8.5 Privacy Enforcement Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Respects `privacy_level` | ⚠️ Not yet implemented | Phase 4 |
| No unauthorized network calls | ✅ Compliant | No network calls yet |
| Logs privacy decisions | ⚠️ Not yet implemented | Phase 3 + 4 |

### 8.6 Security Model Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Input validation (schema) | ✅ Compliant | Pydantic models |
| No hidden execution | ✅ Compliant | Explicit task execution |
| Structured errors | ⚠️ Partial | Need error codes (Phase 5) |
| Fail-fast on violations | ✅ Compliant | Exception handling |

---

## 9. What Does NOT Belong in noema-agent

### 9.1 Explicitly Prohibited Features

❌ **Router Decision Matrix** → Lives in Client  
❌ **Session Timeout Enforcement** → Lives in Client/Orchestrator  
❌ **Session Memory Storage** → Lives in Client  
❌ **Model Selection** → Decided upstream  
❌ **Fallback Logic** → Decided by Router  
❌ **Persistent Storage** → No database  
❌ **Background Processing** → No async autonomy  
❌ **Tool Discovery** → No self-modification  

### 9.2 What Lives Upstream (Client/Orchestrator)

- ✅ User input collection
- ✅ Session creation and management
- ✅ Router Decision Matrix execution
- ✅ Model selection
- ✅ Fallback logic
- ✅ Session memory (authoritative storage)
- ✅ 45-minute timeout enforcement

### 9.3 What Lives in noema-agent

- ✅ Invocation Boundary (`/invoke` endpoint)
- ✅ Task execution (deterministic)
- ✅ Input validation (schema)
- ✅ Privacy enforcement (guard rail)
- ✅ Structured response generation
- ✅ Execution logging (observability)

---

## 10. Clean Integration Plan (Step-by-Step)

### 10.1 Immediate Actions (No Code Changes)

✅ **1. Confirm architectural alignment**
   - Current implementation is compliant
   - No routing logic present
   - No session management present
   - Stateless execution preserved

✅ **2. Document boundaries**
   - This integration plan serves as boundary specification
   - Share with orchestrator/client teams

### 10.2 Phase 1: Contract Enrichment (Week 1)

**Objective:** Align Invocation Boundary with design specs.

**Tasks:**
1. ✅ Add `request_id`, `timestamp`, `privacy_level`, `trace_id` to `InvocationRequest` (optional fields)
2. ✅ Add `request_id`, `executed_at`, `execution_time_ms` to `InvocationResponse`
3. ✅ Update `/health` to return supported tasks
4. ✅ Add unit tests for new fields
5. ✅ Update `test_api.py` with contract validation

**Deliverable:** Extended contract, backward-compatible.

### 10.3 Phase 2: Task Registry (Week 1-2)

**Objective:** Replace hardcoded task logic with registry pattern.

**Tasks:**
1. ✅ Create `app/tasks/` package structure
2. ✅ Implement `BaseTask` interface
3. ✅ Refactor `EchoTask` as registry-based
4. ✅ Update `executor.py` to use registry
5. ✅ Add unit tests for registry and tasks
6. ✅ Update documentation

**Deliverable:** Extensible task system.

### 10.4 Phase 3: Observability (Week 2)

**Objective:** Add structured logging aligned with specs.

**Tasks:**
1. ✅ Add structured logging to executor
2. ✅ Log all required fields (session_id, request_id, task_type, status, etc.)
3. ✅ Add execution timing instrumentation
4. ✅ Optional: Add `/metrics` endpoint
5. ✅ Configure log format (JSON recommended)

**Deliverable:** Production-ready logging.

### 10.5 Phase 4: Privacy Guards (Week 3)

**Objective:** Add privacy constraint enforcement.

**Tasks:**
1. ✅ Add `privacy_level` validation
2. ✅ Block network-dependent tasks if `privacy_level == "local"`
3. ✅ Log privacy enforcement events
4. ✅ Add tests for privacy violations
5. ✅ Document privacy enforcement policy

**Deliverable:** Defense-in-depth privacy protection.

### 10.6 Phase 5: Error Standardization (Week 3)

**Objective:** Align error responses with specs.

**Tasks:**
1. ✅ Define structured error codes
2. ✅ Update error response format
3. ✅ Add error code documentation
4. ✅ Update tests for new error format

**Deliverable:** Machine-readable errors.

---

## 11. Integration with Upstream Systems

### 11.1 Client/Orchestrator Interface

**What Client/Orchestrator MUST Provide:**
- ✅ `session_id` (generated client-side)
- ✅ `request_id` (UUID)
- ✅ `task_type` (from router decision)
- ✅ `payload` (task-specific data)
- ✅ `privacy_level` (from user preference or router)
- ✅ `timestamp` (request creation time)
- ⚠️ Optional: `trace_id` (for distributed tracing)

**What noema-agent PROVIDES:**
- ✅ Execution result or error
- ✅ Echoed `session_id` and `request_id`
- ✅ Execution metadata (timestamp, duration)
- ✅ Structured status codes

### 11.2 Session Management Handoff

**Client/Orchestrator Responsibilities:**
- Session creation
- Session timeout (45 minutes)
- Session memory storage
- Session expiration enforcement

**noema-agent Responsibilities:**
- Accept `session_id` for traceability
- Echo `session_id` in response
- **DO NOT** validate or enforce session lifecycle

### 11.3 Router Integration

**Router outputs** → **noema-agent inputs:**

| Router Output | noema-agent Field | Notes |
|---------------|-------------------|-------|
| `route = "local"` | `task_type` | Determines which task to execute |
| `model = "gpt-4"` | Not used | Model selection happens upstream |
| `privacy_level = "local"` | `privacy_level` | For enforcement only |
| `question_id` | `request_id` | For traceability |

**noema-agent does NOT:**
- ❌ Receive router output directly
- ❌ Make routing decisions
- ❌ Select models

**noema-agent ONLY:**
- ✅ Executes pre-determined tasks
- ✅ Respects privacy constraints
- ✅ Returns structured results

---

## 12. Testing Strategy

### 12.1 Unit Tests

**Coverage:**
- ✅ Task registry (get, list, unsupported)
- ✅ Individual task implementations
- ✅ Executor logic (success, error, unsupported)
- ✅ Model validation (Pydantic)
- ✅ Privacy enforcement guards

### 12.2 Integration Tests

**Coverage:**
- ✅ `/invoke` endpoint (success, error cases)
- ✅ `/health` endpoint
- ✅ Contract validation (request/response fields)
- ✅ Error response formats

### 12.3 Compliance Tests

**Coverage:**
- ✅ Stateless verification (no persistence)
- ✅ Determinism verification (same input → same output)
- ✅ Privacy enforcement (local blocks network)
- ✅ Invocation boundary (no hidden side effects)

---

## 13. Documentation Deliverables

### 13.1 User-Facing Documentation

- ✅ Updated `README.md` with contract details
- ✅ API reference with all fields
- ✅ Task catalog (supported task types)
- ✅ Error code reference

### 13.2 Developer Documentation

- ✅ This integration plan
- ✅ Task development guide
- ✅ Architecture decision records (ADRs)
- ✅ Compliance checklist

### 13.3 Operational Documentation

- ✅ Logging format specification
- ✅ Observability guide
- ✅ Deployment instructions
- ✅ Troubleshooting guide

---

## 14. Success Criteria

### 14.1 Architectural Compliance

✅ **All design specifications satisfied:**
- Invocation Boundary respected
- No routing logic present
- Stateless execution maintained
- Session management not implemented (correct)
- Privacy enforcement available (optional)

### 14.2 Functional Requirements

✅ **Core functionality:**
- Accept InvocationRequest
- Execute deterministic tasks
- Return InvocationResponse
- Log all invocations
- Handle errors gracefully

### 14.3 Integration Readiness

✅ **Upstream compatibility:**
- Contract aligned with orchestrator
- Session handoff clarified
- Router boundary respected
- Privacy constraints documented

---

## 15. Next Steps (After Approval)

1. **Review this integration plan** with team
2. **Confirm contract alignment** with orchestrator/client teams
3. **Approve phased implementation** (Phases 1-5)
4. **Begin Phase 1** (contract enrichment)
5. **Iterate** based on integration testing

---

## 16. Conclusion

### 16.1 Key Findings

✅ **noema-agent X-2 is architecturally compliant** with Noesis Noema design specifications.

⚠️ **Minor enhancements needed:**
- Contract enrichment (`request_id`, `timestamp`, `privacy_level`)
- Task registry for extensibility
- Structured logging for observability
- Privacy enforcement guards (optional)
- Error code standardization

❌ **No fundamental changes required:**
- No routing logic needed
- No session management needed
- No persistence needed
- Current stateless design is correct

### 16.2 Architectural Confidence

The current implementation **correctly interprets** the execution layer role:
- Accepts post-routing requests
- Executes constrained tasks
- Returns structured responses
- Maintains no state
- Makes no decisions

This is **exactly what the design specifications require**.

---

**End of Integration Plan**

**Status:** ✅ Ready for review and phased implementation  
**Recommendation:** Proceed with Phase 1 (contract enrichment) after team approval.

