"""
Structured logging for Invocation Boundary.

Emits JSON-formatted log events with required observability fields.
"""

import json
import logging
from datetime import datetime, timezone

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


def _get_timestamp() -> str:
    """Get current ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log_invocation_started(
    trace_id: str,
    request_id: str,
    session_id: str,
    task_type: str
) -> None:
    """
    Log invocation_started event.

    Args:
        trace_id: Distributed tracing identifier
        request_id: Unique request identifier
        session_id: Session identifier
        task_type: Task type being executed
    """
    event = {
        "event_name": "invocation_started",
        "timestamp": _get_timestamp(),
        "trace_id": trace_id,
        "request_id": request_id,
        "session_id": session_id,
        "task_type": task_type
    }
    logger.info(json.dumps(event))


def log_invocation_completed(
    trace_id: str,
    request_id: str,
    session_id: str,
    task_type: str,
    status: str,
    execution_time_ms: int
) -> None:
    """
    Log invocation_completed event.

    Args:
        trace_id: Distributed tracing identifier
        request_id: Unique request identifier
        session_id: Session identifier
        task_type: Task type executed
        status: Execution status (success or error)
        execution_time_ms: Execution duration in milliseconds
    """
    event = {
        "event_name": "invocation_completed",
        "timestamp": _get_timestamp(),
        "trace_id": trace_id,
        "request_id": request_id,
        "session_id": session_id,
        "task_type": task_type,
        "status": status,
        "execution_time_ms": execution_time_ms
    }
    logger.info(json.dumps(event))


def log_error_raised(
    trace_id: str,
    request_id: str,
    session_id: str,
    task_type: str,
    error_code: str,
    error_message: str,
    recoverable: bool
) -> None:
    """
    Log error_raised event.

    Args:
        trace_id: Distributed tracing identifier
        request_id: Unique request identifier
        session_id: Session identifier
        task_type: Task type that failed
        error_code: Error code (E-EXEC-001, etc.)
        error_message: Human-readable error message
        recoverable: Whether retry might succeed
    """
    event = {
        "event_name": "error_raised",
        "timestamp": _get_timestamp(),
        "trace_id": trace_id,
        "request_id": request_id,
        "session_id": session_id,
        "task_type": task_type,
        "error_code": error_code,
        "error_message": error_message,
        "recoverable": recoverable
    }
    logger.error(json.dumps(event))

