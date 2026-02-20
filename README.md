# noema-agent

> Stateless execution layer for Noesis Noema architecture.

## Vision

noema-agent is the execution layer of the Noesis Noema system.

- Stateless task execution with no routing or persistence
- Structured logging with trace_id propagation
- Deterministic execution with timing instrumentation
- Strict schema validation and error handling

This repository is **architecture-first**:  
we define the system as diagrams and specifications before we write any executable code.

---

## Phase 2A: Critical Compliance

**Status**: Implemented  
**Version**: 2.0.0

This is the Execution Layer implementation — stateless, deterministic, no routing.

### Architecture Principles

- ✅ Stateless execution
- ✅ No decision-making authority
- ✅ No routing logic
- ✅ No persistence layer
- ✅ Accept Invocation Boundary request
- ✅ Execute constrained task only
- ✅ Return structured JSON response
- ✅ Structured logging with trace_id propagation
- ✅ Timing instrumentation
- ✅ Strict schema validation (extra fields rejected)

### Quick Start

1. **Set up virtual environment** (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

4. **Run compliance tests**:
   ```bash
   source venv/bin/activate
   python test_compliance.py
   ```

5. **Run unit tests**:
   ```bash
   source venv/bin/activate
   pytest tests/
   ```

### API Reference

**Endpoints:**

- `GET /` — Service information
- `GET /health` — Health check with supported tasks
- `POST /invoke` — Invocation Boundary (main execution endpoint)

**POST /invoke**

Request:
```json
{
  "session_id": "uuid",
  "request_id": "uuid",
  "task_type": "string",
  "payload": {},
  "timestamp": "ISO-8601",
  "trace_id": "uuid",
  "privacy_level": "local | hybrid | cloud (optional)"
}
```

Response (Success):
```json
{
  "session_id": "uuid",
  "request_id": "uuid",
  "trace_id": "uuid",
  "status": "success",
  "result": {},
  "error": null,
  "timestamp": "ISO-8601",
  "execution_time_ms": 50
}
```

Response (Error):
```json
{
  "session_id": "uuid",
  "request_id": "uuid",
  "trace_id": "uuid",
  "status": "error",
  "result": {},
  "error": {
    "code": "E-EXEC-001",
    "message": "Unsupported task type: xyz",
    "recoverable": false,
    "trace_id": "uuid",
    "timestamp": "ISO-8601"
  },
  "timestamp": "ISO-8601",
  "execution_time_ms": 25
}
```

**Supported Task Types**:
- `echo` — Returns payload unchanged

**Error Codes**:
- `E-EXEC-001` — UnsupportedTask
- `E-EXEC-002` — ValidationError
- `E-EXEC-003` — ExecutionFailure
- `E-EXEC-004` — PrivacyViolation
- `E-EXEC-005` — PayloadTooLarge

### Structured Logging

All invocations emit JSON-formatted log events:

**invocation_started**:
```json
{
  "event_name": "invocation_started",
  "timestamp": "ISO-8601",
  "trace_id": "uuid",
  "request_id": "uuid",
  "session_id": "uuid",
  "task_type": "echo"
}
```

**invocation_completed**:
```json
{
  "event_name": "invocation_completed",
  "timestamp": "ISO-8601",
  "trace_id": "uuid",
  "request_id": "uuid",
  "session_id": "uuid",
  "task_type": "echo",
  "status": "success",
  "execution_time_ms": 50
}
```

**error_raised**:
```json
{
  "event_name": "error_raised",
  "timestamp": "ISO-8601",
  "trace_id": "uuid",
  "request_id": "uuid",
  "session_id": "uuid",
  "task_type": "unsupported",
  "error_code": "E-EXEC-001",
  "error_message": "Unsupported task type: unsupported",
  "recoverable": false
}
```

### Project Structure

```
noema-agent/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models (request/response/error)
│   ├── executor.py          # Task execution logic with timing
│   └── logging_utils.py     # Structured JSON logging
├── tests/
│   ├── __init__.py
│   └── test_phase2a.py      # Unit tests for compliance
├── requirements.txt         # Python dependencies
├── test_compliance.py       # Integration tests for Phase 2A
├── GUARDRAIL-CONTRACT.md    # Enforcement contract
├── VALIDATION-SUMMARY.md    # Compliance validation report
└── README.md                # This file
```

### Environment

- Python 3.14.3
- FastAPI
- Pydantic 2.x with strict validation
- No database
- No Docker (minimal implementation)

### Compliance

This implementation passes all Phase 2A compliance gates:

- ✅ Gate 1: Architectural Purity (no routing, sessions, persistence, autonomy)
- ✅ Gate 2: Observability Compliance (structured logging, trace_id, events)
- ✅ Gate 3: Error Doctrine Compliance (error codes, structured format)
- ✅ Gate 4: Schema Compliance (required fields, strict validation)

