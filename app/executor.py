"""
Constrained task executor.

Pure execution logic with no routing or decision-making.
Each task type is handled deterministically.
"""

import time
from datetime import datetime, timezone

from app.models import (
    InvocationRequest,
    InvocationResponse,
    ErrorDetail,
    ErrorCode,
    ExecutionStatus
)
from app.logging_utils import (
    log_invocation_started,
    log_invocation_completed,
    log_error_raised
)


def _get_timestamp() -> str:
    """Get current ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def execute_task(request: InvocationRequest) -> InvocationResponse:
    """
    Execute a constrained task based on task_type.

    This is a deterministic executor with no business logic or routing.
    Supported task types:
        - "echo": Returns the payload unchanged

    Args:
        request: InvocationRequest with task_type and payload

    Returns:
        InvocationResponse with status, result, and optional error
    """
    start_time = time.perf_counter()

    # Log invocation started
    log_invocation_started(
        trace_id=request.trace_id,
        request_id=request.request_id,
        session_id=request.session_id,
        task_type=request.task_type
    )

    task_type = request.task_type
    session_id = request.session_id
    request_id = request.request_id
    trace_id = request.trace_id
    payload = request.payload

    # Execute task
    if task_type == "echo":
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        # Log completion
        log_invocation_completed(
            trace_id=trace_id,
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            status="success",
            execution_time_ms=execution_time_ms
        )

        return InvocationResponse(
            session_id=session_id,
            request_id=request_id,
            trace_id=trace_id,
            status=ExecutionStatus.SUCCESS,
            result=payload,
            error=None,
            timestamp=_get_timestamp(),
            execution_time_ms=execution_time_ms
        )

    # Unsupported task type
    execution_time_ms = int((time.perf_counter() - start_time) * 1000)
    error_timestamp = _get_timestamp()

    error_detail = ErrorDetail(
        code=ErrorCode.E_EXEC_001,
        message=f"Unsupported task type: {task_type}",
        recoverable=False,
        trace_id=trace_id,
        timestamp=error_timestamp
    )

    # Log error
    log_error_raised(
        trace_id=trace_id,
        request_id=request_id,
        session_id=session_id,
        task_type=task_type,
        error_code=error_detail.code.value,
        error_message=error_detail.message,
        recoverable=error_detail.recoverable
    )

    # Log completion
    log_invocation_completed(
        trace_id=trace_id,
        request_id=request_id,
        session_id=session_id,
        task_type=task_type,
        status="error",
        execution_time_ms=execution_time_ms
    )

    return InvocationResponse(
        session_id=session_id,
        request_id=request_id,
        trace_id=trace_id,
        status=ExecutionStatus.ERROR,
        result={},
        error=error_detail,
        timestamp=error_timestamp,
        execution_time_ms=execution_time_ms
    )
