"""
Constrained task executor.

Pure execution logic with no routing or decision-making.
Each task type is handled deterministically.
"""

import time
import uuid
from datetime import datetime, timezone

from app.models import (
    InvocationRequest,
    InvocationResponse,
    ErrorDetail,
    ErrorCode,
    ExecutionStatus,
    EvidenceAttachment
)
from app.constraint_engine import check_constraints
from app.logging_utils import (
    log_constraint_rejected,
    log_error_raised,
    log_invocation_completed,
    log_invocation_started,
)


def _get_timestamp() -> str:
    """Get current ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_constraint_name(error_code: "ErrorCode") -> str:
    """
    Map an error code to the constraint check name for observability.

    Used in constraint_rejected log events to identify which specific
    check produced the violation, without exposing payload content.
    """
    mapping = {
        ErrorCode.E_EXEC_005: "check_payload_size",
        ErrorCode.E_EXEC_004: "check_privacy_coherence",
        ErrorCode.E_EXEC_002: "check_payload_size",  # serialization failure
    }
    return mapping.get(error_code, "check_unknown")


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
    trace_id = str(uuid.uuid4())

    # Log invocation started
    log_invocation_started(
        trace_id=trace_id,
        request_id=request.request_id,
        session_id=request.session_id,
        task_type=request.task_type
    )

    task_type = request.task_type
    session_id = request.session_id
    request_id = request.request_id
    payload = request.payload

    # EPIC2: Constraint enforcement gate.
    # Runs after schema validation, before any task dispatch.
    # Fail-fast: if any structural constraint is violated, return immediately.
    constraint_error = check_constraints(request, trace_id)
    if constraint_error is not None:
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        log_constraint_rejected(
            trace_id=trace_id,
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            error_code=constraint_error.code.value,
            constraint_name=_resolve_constraint_name(constraint_error.code),
        )

        log_invocation_completed(
            trace_id=trace_id,
            request_id=request_id,
            session_id=session_id,
            task_type=task_type,
            status="error",
            execution_time_ms=execution_time_ms,
        )

        return InvocationResponse(
            session_id=session_id,
            request_id=request_id,
            trace_id=trace_id,
            status=ExecutionStatus.ERROR,
            result={},
            error=constraint_error,
            timestamp=_get_timestamp(),
            execution_time_ms=execution_time_ms,
            evidence=[],
        )

    # Execute task
    if task_type == "echo":
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)

        # Parse evidence from payload if present
        evidence_list: list[EvidenceAttachment] = []
        if "evidence" in payload and isinstance(payload["evidence"], list):
            for evidence_dict in payload["evidence"]:
                if isinstance(evidence_dict, dict):
                    try:
                        evidence_item = EvidenceAttachment(**evidence_dict)
                        evidence_list.append(evidence_item)
                    except Exception:
                        # Skip invalid evidence items silently
                        pass

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
            execution_time_ms=execution_time_ms,
            evidence=evidence_list
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
        execution_time_ms=execution_time_ms,
        evidence=[]
    )
