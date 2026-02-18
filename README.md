# noema-agent

> Server-side brain and router for Noesis Noema — a private, on-device RAG client for macOS/iOS.

## Vision

noema-agent is the backend counterpart of Noesis Noema.

- It receives structured requests from the client.
- It applies routing and policy decisions.
- It orchestrates local / VPC / cloud LLMs and RAG pipelines.
- It always explains **how** a response was produced (evidence, routing, constraints).

This repository is **architecture-first**:  
we define the system as diagrams and specifications before we write any executable code.

---

## X-2: Minimal API (v2)

**Status**: Implemented

This is the Execution Layer implementation — stateless, deterministic, no routing.

### Architecture Principles

- ✅ Stateless execution
- ✅ No decision-making authority
- ✅ No routing logic
- ✅ No persistence layer
- ✅ Accept Invocation Boundary request
- ✅ Execute constrained task only
- ✅ Return structured JSON response

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

4. **Run automated tests** (in a new terminal):
   ```bash
   source venv/bin/activate
   pip install requests  # Only needed for testing
   python test_api.py
   ```

5. **Test the API manually**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Echo task
   curl -X POST http://localhost:8000/invoke \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "test-123",
       "task_type": "echo",
       "payload": {"message": "Hello, Noema!"}
     }'
   
   # Unsupported task (returns error)
   curl -X POST http://localhost:8000/invoke \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "test-456",
       "task_type": "unsupported",
       "payload": {}
     }'
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
  "session_id": "string",
  "task_type": "string",
  "payload": {}
}
```

Response:
```json
{
  "session_id": "string",
  "status": "success | error",
  "result": {},
  "error": "string | null"
}
```

**Supported Task Types**:
- `echo` — Returns payload unchanged

### Project Structure

```
noema-agent/
├── app/
│   ├── __init__.py       # Package initialization
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models (InvocationRequest/Response)
│   └── executor.py       # Task execution logic
├── requirements.txt      # Python dependencies
├── test_api.py          # Automated API tests
└── README.md            # This file
```

### Environment

- Python 3.14.3
- FastAPI
- No database
- No Docker (minimal implementation)
