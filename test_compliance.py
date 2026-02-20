#!/usr/bin/env python3
"""
Phase 2A Compliance Tests for noema-agent

Tests trace_id propagation, structured errors, execution_time_ms, and strict schema enforcement.
"""

import requests
import json
import uuid
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"


def test_trace_id_propagation():
    """Test that trace_id is echoed in response"""
    trace_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"message": "test"},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Trace ID propagation test: {response.status_code}")
    print(f"  Request trace_id: {trace_id}")

    result = response.json()
    print(f"  Response trace_id: {result.get('trace_id')}")
    print(f"  Response: {json.dumps(result, indent=2)}\n")

    return (response.status_code == 200 and
            result.get("trace_id") == trace_id and
            result.get("request_id") == request_id and
            result.get("session_id") == session_id)


def test_structured_error_shape():
    """Test that errors have structured format with code, message, recoverable, trace_id"""
    trace_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "unsupported_task",
        "payload": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id
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
            error["code"] == "E-EXEC-001")


def test_execution_time_ms_presence():
    """Test that execution_time_ms is present in all responses"""
    trace_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {"data": "test"},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id
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
    trace_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id,
        "extra_field": "should_be_rejected"  # This should be rejected
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Strict schema enforcement test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    # Should return 422 Unprocessable Entity due to extra field
    return response.status_code == 422


def test_missing_required_field():
    """Test that missing required fields are rejected"""
    payload = {
        "session_id": str(uuid.uuid4()),
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {},
        "timestamp": datetime.utcnow().isoformat() + "Z"
        # Missing trace_id - should fail
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Missing required field test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    # Should return 422 Unprocessable Entity due to missing field
    return response.status_code == 422


def test_timestamp_in_response():
    """Test that timestamp is present in response"""
    trace_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id
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
    trace_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Without privacy_level
    payload = {
        "session_id": session_id,
        "request_id": request_id,
        "task_type": "echo",
        "payload": {},
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id
    }

    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Privacy level optional test: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")

    return response.status_code == 200


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 2A Compliance Tests for noema-agent")
    print("=" * 70 + "\n")

    try:
        tests = [
            ("Trace ID propagation", test_trace_id_propagation),
            ("Structured error shape", test_structured_error_shape),
            ("Execution time presence", test_execution_time_ms_presence),
            ("Strict schema enforcement", test_strict_schema_enforcement),
            ("Missing required field rejection", test_missing_required_field),
            ("Timestamp in response", test_timestamp_in_response),
            ("Privacy level optional", test_privacy_level_optional),
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

