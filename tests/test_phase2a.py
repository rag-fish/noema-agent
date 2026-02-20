"""
Unit tests for Phase 2A compliance.

Tests models, executor, and logging without HTTP layer.
"""

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


def test_invocation_request_valid():
    """Test valid InvocationRequest creation"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"message": "test"},
        timestamp="2026-02-20T10:00:00Z",
        trace_id="trace-789"
    )
    assert request.session_id == "session-123"
    assert request.request_id == "request-456"
    assert request.trace_id == "trace-789"


def test_invocation_request_rejects_extra_fields():
    """Test that extra fields are rejected"""
    with pytest.raises(Exception):
        InvocationRequest(
            session_id="session-123",
            request_id="request-456",
            task_type="echo",
            payload={},
            timestamp="2026-02-20T10:00:00Z",
            trace_id="trace-789",
            extra_field="should_fail"
        )


def test_invocation_request_privacy_level_optional():
    """Test that privacy_level is optional"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
        timestamp="2026-02-20T10:00:00Z",
        trace_id="trace-789"
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
            timestamp="2026-02-20T10:00:00Z",
            trace_id="trace-789",
            privacy_level=level
        )
        assert request.privacy_level == level


def test_error_detail_structure():
    """Test ErrorDetail structure"""
    error = ErrorDetail(
        code=ErrorCode.E_EXEC_001,
        message="Test error",
        recoverable=False,
        trace_id="trace-123",
        timestamp="2026-02-20T10:00:00Z"
    )
    assert error.code == ErrorCode.E_EXEC_001
    assert error.message == "Test error"
    assert error.recoverable is False
    assert error.trace_id == "trace-123"
    assert error.timestamp == "2026-02-20T10:00:00Z"


def test_invocation_response_success():
    """Test successful InvocationResponse"""
    response = InvocationResponse(
        session_id="session-123",
        request_id="request-456",
        trace_id="trace-789",
        status=ExecutionStatus.SUCCESS,
        result={"data": "test"},
        error=None,
        timestamp="2026-02-20T10:00:00Z",
        execution_time_ms=50
    )
    assert response.status == ExecutionStatus.SUCCESS
    assert response.result == {"data": "test"}
    assert response.error is None
    assert response.execution_time_ms == 50


def test_invocation_response_error():
    """Test error InvocationResponse"""
    error_detail = ErrorDetail(
        code=ErrorCode.E_EXEC_001,
        message="Test error",
        recoverable=False,
        trace_id="trace-789",
        timestamp="2026-02-20T10:00:00Z"
    )
    response = InvocationResponse(
        session_id="session-123",
        request_id="request-456",
        trace_id="trace-789",
        status=ExecutionStatus.ERROR,
        result={},
        error=error_detail,
        timestamp="2026-02-20T10:00:00Z",
        execution_time_ms=25
    )
    assert response.status == ExecutionStatus.ERROR
    assert response.error.code == ErrorCode.E_EXEC_001
    assert response.execution_time_ms == 25


def test_executor_echo_task():
    """Test executor with echo task"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"message": "hello"},
        timestamp="2026-02-20T10:00:00Z",
        trace_id="trace-789"
    )
    response = execute_task(request)

    assert response.status == ExecutionStatus.SUCCESS
    assert response.result == {"message": "hello"}
    assert response.error is None
    assert response.session_id == "session-123"
    assert response.request_id == "request-456"
    assert response.trace_id == "trace-789"
    assert response.execution_time_ms >= 0
    assert len(response.timestamp) > 0


def test_executor_unsupported_task():
    """Test executor with unsupported task"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="unsupported",
        payload={},
        timestamp="2026-02-20T10:00:00Z",
        trace_id="trace-789"
    )
    response = execute_task(request)

    assert response.status == ExecutionStatus.ERROR
    assert response.result == {}
    assert response.error is not None
    assert response.error.code == ErrorCode.E_EXEC_001
    assert "Unsupported task type" in response.error.message
    assert response.error.recoverable is False
    assert response.error.trace_id == "trace-789"
    assert response.session_id == "session-123"
    assert response.request_id == "request-456"
    assert response.trace_id == "trace-789"
    assert response.execution_time_ms >= 0


def test_executor_trace_id_propagation():
    """Test that trace_id is propagated through executor"""
    trace_id = "test-trace-id-999"
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={},
        timestamp="2026-02-20T10:00:00Z",
        trace_id=trace_id
    )
    response = execute_task(request)

    assert response.trace_id == trace_id


def test_executor_deterministic():
    """Test that executor is deterministic for same input"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"test": "data"},
        timestamp="2026-02-20T10:00:00Z",
        trace_id="trace-789"
    )

    response1 = execute_task(request)
    response2 = execute_task(request)

    # Results should be identical
    assert response1.result == response2.result
    assert response1.status == response2.status

