#!/usr/bin/env python3
"""
Compliance Tests for noema-agent (Phase 2A + X-4 + X-5)

X-5: trace_id is now Execution Layer-generated.
     Sending trace_id in request must return 422.
"""

import re
import requests
import json
import uuid
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:8000"

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def _is_valid_uuid(value: str) -> bool:
    return bool(UUID_PATTERN.match(str(value)))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def test_trace_id_generated_by_server():
    """X-5: trace_id must be server-generated; response contains valid UUID trace_id"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"message": "test"},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Server-generated trace_id test: {response.status_code}")

    result = response.json()
    print(f"  Response trace_id: {result.get('trace_id')}")
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            "trace_id" in result and
            isinstance(result["trace_id"], str) and
            _is_valid_uuid(result["trace_id"]) and
            result.get("request_id") == request_id and
            result.get("session_id") == session_id)


def test_client_supplied_trace_id_rejected():
    """X-5: Supplying trace_id in request must be rejected with 422"""
    payload = {
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
        "trace_id": str(uuid.uuid4()),  # must be rejected
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Client trace_id rejected test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    return response.status_code == 422


def test_trace_id_unique_per_invocation():
    """X-5: Each invocation must produce a unique trace_id"""
    payload = {
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
    }

    r1 = requests.post(f"{BASE_URL}/invoke", json=payload)
    r2 = requests.post(f"{BASE_URL}/invoke", json=payload)
    trace1 = r1.json().get("trace_id")
    trace2 = r2.json().get("trace_id")
    print(f"✓ Unique trace_id per invocation: {trace1} != {trace2}\n")

    return (r1.status_code == 200 and
            r2.status_code == 200 and
            trace1 != trace2 and
            _is_valid_uuid(trace1) and
            _is_valid_uuid(trace2))


def test_structured_error_shape():
    """Test that errors have structured format with code, message, recoverable, trace_id"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "unsupported_task",
        "payload": {},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Structured error shape test: {response.status_code}")

    result = response.json()
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    error = result.get("error")
    return (response.status_code == 200 and
            result.get("status") == "error" and
            error is not None and
            "code" in error and
            "message" in error and
            "recoverable" in error and
            "trace_id" in error and
            "timestamp" in error and
            error["code"] == "E-EXEC-001" and
            error["trace_id"] == result.get("trace_id") and
            _is_valid_uuid(result.get("trace_id", "")))


def test_execution_time_ms_presence():
    """Test that execution_time_ms is present in all responses"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"data": "test"},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Execution time presence test: {response.status_code}")

    result = response.json()
    print(f"  execution_time_ms: {result.get('execution_time_ms')}")
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            "execution_time_ms" in result and
            isinstance(result["execution_time_ms"], int) and
            result["execution_time_ms"] >= 0)


def test_strict_schema_enforcement():
    """Test that extra fields are rejected (Pydantic extra='forbid')"""
    payload = {
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
        "extra_field": "should_be_rejected"
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Strict schema enforcement test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    return response.status_code == 422


def test_missing_required_field():
    """Test that missing required fields are rejected"""
    payload = {
        # Missing session_id — must fail
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Missing required field test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    return response.status_code == 422


def test_timestamp_in_response():
    """Test that timestamp is present in response"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Timestamp in response test: {response.status_code}")

    result = response.json()
    print(f"  Response timestamp: {result.get('timestamp')}")
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            "timestamp" in result and
            isinstance(result["timestamp"], str))


def test_privacy_level_optional():
    """Test that privacy_level is optional"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Privacy level optional test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    return response.status_code == 200


def test_evidence_attachment_in_response():
    """Test that evidence attachments are included in response (X-4)"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
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
                    "score": 0.95
                }
            ]
        },
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Evidence attachment test: {response.status_code}")

    result = response.json()
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            "evidence" in result and
            isinstance(result["evidence"], list) and
            len(result["evidence"]) == 1 and
            result["evidence"][0]["source_id"] == "doc-001#p3" and
            result["evidence"][0]["snippet"] == "This is a human-readable excerpt from page 3.")


def test_evidence_source_reference_fields():
    """Test that evidence contains all required source reference fields (X-4 DoD)"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {
            "result": "answer",
            "evidence": [
                {
                    "source_id": "doc-042#section-2.1",
                    "source_type": "web",
                    "location": "§2.1",
                    "snippet": "Human-readable evidence text for DoD compliance."
                }
            ]
        },
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Evidence source reference fields test: {response.status_code}")

    result = response.json()
    evidence = result.get("evidence", [])

    if len(evidence) > 0:
        ev = evidence[0]
        print(f"  source_id: {ev.get('source_id')}")
        print(f"  source_type: {ev.get('source_type')}")
        print(f"  location: {ev.get('location')}")
        print(f"  snippet: {ev.get('snippet')[:50]}...")
        print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            len(evidence) > 0 and
            "source_id" in evidence[0] and
            "source_type" in evidence[0] and
            "location" in evidence[0] and
            "snippet" in evidence[0] and
            len(evidence[0]["snippet"]) > 0)


def test_evidence_human_readable_format():
    """Test that evidence format is human-readable (X-4 DoD)"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {
            "answer": "test",
            "evidence": [
                {
                    "source_id": "note-123",
                    "source_type": "note",
                    "location": "line 5",
                    "snippet": "これは日本語のテキストです。This is readable text in multiple languages.",
                    "score": 0.88
                }
            ]
        },
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Evidence human-readable format test: {response.status_code}")

    result = response.json()
    evidence = result.get("evidence", [])

    if len(evidence) > 0:
        snippet = evidence[0].get("snippet", "")
        print(f"  Snippet: {snippet}")
        print(f"  Snippet length: {len(snippet)}")
        print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            len(evidence) > 0 and
            len(evidence[0].get("snippet", "")) > 0 and
            isinstance(evidence[0].get("snippet"), str))


def test_echo_without_evidence_still_works():
    """Test that echo task still works without evidence (backward compatibility)"""
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"message": "test without evidence"},
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Echo without evidence test: {response.status_code}")

    result = response.json()
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            result.get("status") == "success" and
            "evidence" in result and
            result["evidence"] == [])


if __name__ == "__main__":
    print("=" * 70)
    print("Compliance Tests for noema-agent (Phase 2A + X-4 + X-5)")
    print("=" * 70 + "\n")

    try:
        tests = [
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
        for name, test_func in tests:
            try:
                if test_func():
                    print(f"✅ {name} PASSED\n")
                    passed += 1
                else:
                    print(f"❌ {name} FAILED\n")
            except Exception as e:
                print(f"❌ {name} ERROR: {e}\n")

        print("=" * 70)
        print(f"Results: {passed}/{len(tests)} tests passed")
        print("=" * 70)

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server at", BASE_URL)
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")

