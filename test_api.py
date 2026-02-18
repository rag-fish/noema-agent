#!/usr/bin/env python3
"""
Test script for noema-agent X-2 Minimal API
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"✓ Health check: {response.status_code}")
    print(f"  Response: {response.json()}\n")
    return response.status_code == 200

def test_root():
    """Test root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    print(f"✓ Root endpoint: {response.status_code}")
    print(f"  Response: {response.json()}\n")
    return response.status_code == 200

def test_echo_task():
    """Test echo task"""
    payload = {
        "session_id": "test-123",
        "task_type": "echo",
        "payload": {"message": "Hello, Noema!", "data": [1, 2, 3]}
    }
    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Echo task: {response.status_code}")
    print(f"  Request: {json.dumps(payload, indent=2)}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")
    result = response.json()
    return (response.status_code == 200 and
            result["status"] == "success" and
            result["session_id"] == "test-123" and
            result["result"] == payload["payload"])

def test_unsupported_task():
    """Test unsupported task"""
    payload = {
        "session_id": "test-456",
        "task_type": "unsupported_operation",
        "payload": {}
    }
    response = requests.post(f"{BASE_URL}/invoke", json=payload)
    print(f"✓ Unsupported task: {response.status_code}")
    print(f"  Request: {json.dumps(payload, indent=2)}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}\n")
    result = response.json()
    return (response.status_code == 200 and
            result["status"] == "error" and
            result["error"] == "unsupported_task")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing noema-agent X-2 Minimal API")
    print("=" * 60 + "\n")

    try:
        tests = [
            ("Root endpoint", test_root),
            ("Health check", test_health),
            ("Echo task (success)", test_echo_task),
            ("Unsupported task (error)", test_unsupported_task),
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

        print("=" * 60)
        print(f"Results: {passed}/{len(tests)} tests passed")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server at", BASE_URL)
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000")
