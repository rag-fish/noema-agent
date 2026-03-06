#!/usr/bin/env python3
"""
API tests for noema-agent.

Uses FastAPI TestClient — no live server required.
Covers: root, health, echo task, unsupported task.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    """Health endpoint returns 200 with executor=ready."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["executor"] == "ready"
    assert "echo" in body["supported_tasks"]


def test_root():
    """Root endpoint returns service identity."""
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "noema-agent"
    assert body["status"] == "ready"


def test_echo_task():
    """Echo task returns payload unchanged with success status."""
    request_id = str(uuid.uuid4())
    payload = {
        "session_id": "test-123",
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"message": "Hello, Noema!", "data": [1, 2, 3]},
    }
    response = client.post("/invoke", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "success"
    assert body["session_id"] == "test-123"
    assert body["request_id"] == request_id
    assert body["result"] == payload["payload"]
    assert body["error"] is None
    assert isinstance(body["execution_time_ms"], int)
    assert body["execution_time_ms"] >= 0


def test_unsupported_task():
    """Unsupported task_type returns structured E-EXEC-001 error."""
    request_id = str(uuid.uuid4())
    payload = {
        "session_id": "test-456",
        "request_id": request_id,
        "task_type": "unsupported_operation",
        "payload": {},
    }
    response = client.post("/invoke", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "error"
    assert body["error"] is not None
    assert body["error"]["code"] == "E-EXEC-001"
    assert body["error"]["recoverable"] is False
    assert body["error"]["trace_id"] == body["trace_id"]


if __name__ == "__main__":
    # Convenience: run as script and print results
    import json as _json

    _client = TestClient(app)

    tests = [
        ("Root endpoint", test_root),
        ("Health check", test_health),
        ("Echo task (success)", test_echo_task),
        ("Unsupported task (error)", test_unsupported_task),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name} PASSED")
            passed += 1
        except AssertionError as exc:
            print(f"❌ {name} FAILED: {exc}")
        except Exception as exc:
            print(f"❌ {name} ERROR: {exc}")

    print(f"\nResults: {passed}/{len(tests)} tests passed")
