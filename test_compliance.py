#!/usr/bin/env python3
"""
Compliance tests for noema-agent (Phase 2A + X-4 + X-5).

Uses FastAPI TestClient — no live server required.
All tests use assert so pytest correctly reports pass/fail.

X-5: trace_id is Execution Layer-generated.
     Sending trace_id in the request must return 422.
"""

import re
import uuid
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(UUID_PATTERN.match(str(value)))


# ---------------------------------------------------------------------------
# X-5: Execution Identity
# ---------------------------------------------------------------------------


def test_trace_id_generated_by_server():
    """X-5: trace_id must be server-generated; response must contain a valid UUID."""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    response = client.post("/invoke", json={
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"message": "test"},
    })

    assert response.status_code == 200
    body = response.json()
    assert "trace_id" in body
    assert isinstance(body["trace_id"], str)
    assert _is_valid_uuid(body["trace_id"]), f"trace_id is not a valid UUID: {body['trace_id']}"
    assert body["request_id"] == request_id
    assert body["session_id"] == session_id


def test_client_supplied_trace_id_rejected():
    """X-5: Supplying trace_id in the request body must be rejected with 422."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
        "trace_id": str(uuid.uuid4()),  # must be rejected by extra="forbid"
    })

    assert response.status_code == 422


def test_trace_id_unique_per_invocation():
    """X-5: Each invocation must produce a distinct trace_id."""
    payload = {
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
    }

    r1 = client.post("/invoke", json=payload)
    r2 = client.post("/invoke", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200

    trace1 = r1.json()["trace_id"]
    trace2 = r2.json()["trace_id"]

    assert _is_valid_uuid(trace1)
    assert _is_valid_uuid(trace2)
    assert trace1 != trace2, "trace_id must be unique per invocation"


# ---------------------------------------------------------------------------
# Phase 2A: Structured error shape
# ---------------------------------------------------------------------------


def test_structured_error_shape():
    """Errors must have code, message, recoverable, trace_id, timestamp fields."""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    response = client.post("/invoke", json={
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "unsupported_task",
        "payload": {},
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"

    error = body.get("error")
    assert error is not None, "error field must be present"
    assert "code" in error
    assert "message" in error
    assert "recoverable" in error
    assert "trace_id" in error
    assert "timestamp" in error
    assert error["code"] == "E-EXEC-001"
    assert error["trace_id"] == body["trace_id"]
    assert _is_valid_uuid(body["trace_id"])


def test_execution_time_ms_presence():
    """execution_time_ms must be present and be a non-negative integer."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {"data": "test"},
    })

    assert response.status_code == 200
    body = response.json()
    assert "execution_time_ms" in body
    assert isinstance(body["execution_time_ms"], int)
    assert body["execution_time_ms"] >= 0


def test_strict_schema_enforcement():
    """Extra fields must be rejected with 422 (Pydantic extra='forbid')."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
        "extra_field": "should_be_rejected",
    })

    assert response.status_code == 422


def test_missing_required_field():
    """Missing required fields (e.g. session_id) must be rejected with 422."""
    response = client.post("/invoke", json={
        # session_id intentionally omitted
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
    })

    assert response.status_code == 422


def test_timestamp_in_response():
    """Response must include a non-empty timestamp string."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
    })

    assert response.status_code == 200
    body = response.json()
    assert "timestamp" in body
    assert isinstance(body["timestamp"], str)
    assert len(body["timestamp"]) > 0


def test_privacy_level_optional():
    """privacy_level is optional; omitting it must not cause an error."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
    })

    assert response.status_code == 200
    assert response.json()["status"] == "success"


# ---------------------------------------------------------------------------
# X-4: Evidence attachment
# ---------------------------------------------------------------------------


def test_evidence_attachment_in_response():
    """Evidence attachments in the payload must be returned in the response."""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    response = client.post("/invoke", json={
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {
            "message": "test with evidence",
            "evidence": [
                {
                    "source_id": "doc-001#p3",
                    "source_type": "pdf",
                    "location": "p.3",
                    "snippet": "This is a human-readable excerpt from page 3.",
                    "score": 0.95,
                }
            ],
        },
    })

    assert response.status_code == 200
    body = response.json()
    assert "evidence" in body
    assert isinstance(body["evidence"], list)
    assert len(body["evidence"]) == 1
    assert body["evidence"][0]["source_id"] == "doc-001#p3"
    assert body["evidence"][0]["snippet"] == "This is a human-readable excerpt from page 3."


def test_evidence_source_reference_fields():
    """Evidence must contain all required source reference fields (X-4 DoD)."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {
            "result": "answer",
            "evidence": [
                {
                    "source_id": "doc-042#section-2.1",
                    "source_type": "web",
                    "location": "§2.1",
                    "snippet": "Human-readable evidence text for DoD compliance.",
                }
            ],
        },
    })

    assert response.status_code == 200
    body = response.json()
    evidence = body.get("evidence", [])
    assert len(evidence) > 0

    ev = evidence[0]
    assert "source_id" in ev
    assert "source_type" in ev
    assert "location" in ev
    assert "snippet" in ev
    assert len(ev["snippet"]) > 0


def test_evidence_human_readable_format():
    """Evidence snippet must be a non-empty human-readable string (X-4 DoD)."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {
            "answer": "test",
            "evidence": [
                {
                    "source_id": "note-123",
                    "source_type": "note",
                    "location": "line 5",
                    "snippet": "これは日本語のテキストです。This is readable text in multiple languages.",
                    "score": 0.88,
                }
            ],
        },
    })

    assert response.status_code == 200
    body = response.json()
    evidence = body.get("evidence", [])
    assert len(evidence) > 0

    snippet = evidence[0].get("snippet", "")
    assert isinstance(snippet, str)
    assert len(snippet) > 0


def test_echo_without_evidence_still_works():
    """Echo task without evidence must succeed with an empty evidence list."""
    response = client.post("/invoke", json={
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {"message": "test without evidence"},
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "evidence" in body
    assert body["evidence"] == []


# ---------------------------------------------------------------------------
# Convenience: run as script
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _tests = [
        ("Server-generated trace_id (X-5)", test_trace_id_generated_by_server),
        ("Client trace_id rejected (X-5)", test_client_supplied_trace_id_rejected),
        ("Unique trace_id per invocation (X-5)", test_trace_id_unique_per_invocation),
        ("Structured error shape", test_structured_error_shape),
        ("Execution time presence", test_execution_time_ms_presence),
        ("Strict schema enforcement", test_strict_schema_enforcement),
        ("Missing required field rejection", test_missing_required_field),
        ("Timestamp in response", test_timestamp_in_response),
        ("Privacy level optional", test_privacy_level_optional),
        ("Evidence attachment in response (X-4)", test_evidence_attachment_in_response),
        ("Evidence source reference fields (X-4)", test_evidence_source_reference_fields),
        ("Evidence human-readable format (X-4)", test_evidence_human_readable_format),
        ("Echo without evidence (backward compat)", test_echo_without_evidence_still_works),
    ]

    passed = 0
    for _name, _fn in _tests:
        try:
            _fn()
            print(f"✅ {_name} PASSED")
            passed += 1
        except AssertionError as _exc:
            print(f"❌ {_name} FAILED: {_exc}")
        except Exception as _exc:
            print(f"❌ {_name} ERROR: {_exc}")

    print(f"\nResults: {passed}/{len(_tests)} tests passed")
