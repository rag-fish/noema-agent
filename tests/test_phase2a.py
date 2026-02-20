"""
Unit tests for Phase 2A compliance.

Tests models, executor, and logging without HTTP layer.
Updated for X-5: trace_id is now Execution Layer-generated.
"""

import re
import pytest
from app.models import (
    InvocationRequest,
    InvocationResponse,
    ErrorDetail,
    ErrorCode,
    ExecutionStatus,
    PrivacyLevel
)
from app.executor import execute_task

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def _is_valid_uuid(value: str) -> bool:
    return bool(UUID_PATTERN.match(value))


def test_invocation_request_valid():
    """Test valid InvocationRequest creation without trace_id"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"message": "test"},
        timestamp="2026-02-21T10:00:00Z",
    )
    assert request.session_id == "session-123"
    assert request.request_id == "request-456"
    assert not hasattr(request, "trace_id") or "trace_id" not in request.model_fields


def test_invocation_request_rejects_extra_fields():
    """Test that extra fields are rejected, including trace_id"""
    with pytest.raises(Exception):
        InvocationRequest(
            session_id="session-123",
            request_id="request-456",
            task_type="echo",
            payload={},
            extra_field="should_fail"
        )


def test_invocation_request_rejects_trace_id():
    """Test that supplying trace_id as a client field is rejected (X-5)"""
    with pytest.raises(Exception):
        InvocationRequest(
            session_id="session-123",
            request_id="request-456",
            task_type="echo",
            payload={},
            trace_id="client-supplied-trace-id"
        )


def test_invocation_request_timestamp_optional():
    """Test that timestamp is optional (X-5)"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
    )
    assert request.timestamp is None


def test_invocation_request_timestamp_accepted_when_provided():
    """Test that timestamp hint is accepted when provided"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
        timestamp="2026-02-21T10:00:00Z",
    )
    assert request.timestamp == "2026-02-21T10:00:00Z"


def test_invocation_request_privacy_level_optional():
    """Test that privacy_level is optional"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
    )
    assert request.privacy_level is None


def test_invocation_request_privacy_level_valid():
    """Test valid privacy_level values"""
    for level in [PrivacyLevel.LOCAL, PrivacyLevel.HYBRID, PrivacyLevel.CLOUD]:
        request = InvocationRequest(
            session_id="session-123",
            request_id="request-456",
            task_type="echo",
            payload={},
            privacy_level=level
        )
        assert request.privacy_level == level


def test_error_detail_structure():
    """Test ErrorDetail structure"""
    error = ErrorDetail(
        code=ErrorCode.E_EXEC_001,
        message="Test error",
        recoverable=False,
        trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        timestamp="2026-02-21T10:00:00Z"
    )
    assert error.code == ErrorCode.E_EXEC_001
    assert error.message == "Test error"
    assert error.recoverable is False
    assert error.trace_id == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    assert error.timestamp == "2026-02-21T10:00:00Z"


def test_invocation_response_success():
    """Test successful InvocationResponse"""
    response = InvocationResponse(
        session_id="session-123",
        request_id="request-456",
        trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        status=ExecutionStatus.SUCCESS,
        result={"data": "test"},
        error=None,
        timestamp="2026-02-21T10:00:00Z",
        execution_time_ms=50
    )
    assert response.status == ExecutionStatus.SUCCESS
    assert response.result == {"data": "test"}
    assert response.error is None
    assert response.execution_time_ms == 50


def test_invocation_response_error():
    """Test error InvocationResponse"""
    server_trace_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    error_detail = ErrorDetail(
        code=ErrorCode.E_EXEC_001,
        message="Test error",
        recoverable=False,
        trace_id=server_trace_id,
        timestamp="2026-02-21T10:00:00Z"
    )
    response = InvocationResponse(
        session_id="session-123",
        request_id="request-456",
        trace_id=server_trace_id,
        status=ExecutionStatus.ERROR,
        result={},
        error=error_detail,
        timestamp="2026-02-21T10:00:00Z",
        execution_time_ms=25
    )
    assert response.status == ExecutionStatus.ERROR
    assert response.error.code == ErrorCode.E_EXEC_001
    assert response.execution_time_ms == 25
    assert response.error.trace_id == response.trace_id


def test_executor_echo_task():
    """Test executor with echo task; trace_id is server-generated"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"message": "hello"},
    )
    response = execute_task(request)

    assert response.status == ExecutionStatus.SUCCESS
    assert response.result == {"message": "hello"}
    assert response.error is None
    assert response.session_id == "session-123"
    assert response.request_id == "request-456"
    assert isinstance(response.trace_id, str)
    assert len(response.trace_id) > 0
    assert _is_valid_uuid(response.trace_id)
    assert response.execution_time_ms >= 0
    assert len(response.timestamp) > 0


def test_executor_unsupported_task():
    """Test executor with unsupported task; error.trace_id matches response trace_id"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="unsupported",
        payload={},
    )
    response = execute_task(request)

    assert response.status == ExecutionStatus.ERROR
    assert response.result == {}
    assert response.error is not None
    assert response.error.code == ErrorCode.E_EXEC_001
    assert "Unsupported task type" in response.error.message
    assert response.error.recoverable is False
    assert isinstance(response.trace_id, str)
    assert _is_valid_uuid(response.trace_id)
    assert response.error.trace_id == response.trace_id
    assert response.session_id == "session-123"
    assert response.request_id == "request-456"
    assert response.execution_time_ms >= 0


def test_executor_trace_id_generated():
    """Test that trace_id is a server-generated UUID, not client-supplied (X-5)"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
    )
    response = execute_task(request)

    assert isinstance(response.trace_id, str)
    assert _is_valid_uuid(response.trace_id)


def test_executor_trace_id_unique_per_invocation():
    """Test that each invocation produces a different trace_id (X-5)"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
    )
    response1 = execute_task(request)
    response2 = execute_task(request)

    assert response1.trace_id != response2.trace_id


def test_executor_deterministic():
    """Test that result and status are deterministic for same input"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"test": "data"},
    )
    response1 = execute_task(request)
    response2 = execute_task(request)

    # Result and status are deterministic; trace_id is unique per invocation
    assert response1.result == response2.result
    assert response1.status == response2.status
    assert response1.trace_id != response2.trace_id

