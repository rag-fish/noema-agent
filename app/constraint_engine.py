"""
EPIC2 — Agent-Side Constraint Engine.

A stateless, pure-function enforcement gate that validates structural
execution constraints before task dispatch.

This is NOT a policy decision-maker. Policy authority belongs exclusively
to the Client-side ConstraintRuntime (NoesisNoema). This module only
enforces structurally verifiable rules at the Invocation Boundary.

Design reference: docs/epic2-constraint-engine-alignment.md
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from app.models import ErrorCode, ErrorDetail, InvocationRequest, PrivacyLevel

# Maximum allowed payload size in bytes.
# Configurable via environment variable to avoid hardcoded limits.
# Default: 64 KB (65536 bytes).
_DEFAULT_MAX_PAYLOAD_BYTES = 65_536
_MAX_PAYLOAD_BYTES = int(os.environ.get("MAX_PAYLOAD_BYTES", _DEFAULT_MAX_PAYLOAD_BYTES))

# Task types that require network access and are therefore forbidden
# when privacy_level is "local".
# This set will grow as new task types are registered in future EPICs.
_NETWORK_DEPENDENT_TASK_TYPES: frozenset[str] = frozenset()


def _get_timestamp() -> str:
    """Return current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _check_payload_size(
    request: InvocationRequest,
    trace_id: str,
) -> Optional[ErrorDetail]:
    """
    Reject requests whose payload serializes to more than MAX_PAYLOAD_BYTES.

    Uses json.dumps for a canonical byte count rather than str(), which
    produces implementation-dependent output.

    Returns:
        ErrorDetail with E-EXEC-005 if the limit is exceeded, else None.
    """
    try:
        serialized = json.dumps(request.payload, ensure_ascii=False)
        byte_count = len(serialized.encode("utf-8"))
    except (TypeError, ValueError):
        # If the payload cannot be serialized, treat it as a validation error.
        return ErrorDetail(
            code=ErrorCode.E_EXEC_002,
            message="Payload could not be serialized for size validation.",
            recoverable=False,
            trace_id=trace_id,
            timestamp=_get_timestamp(),
        )

    if byte_count > _MAX_PAYLOAD_BYTES:
        return ErrorDetail(
            code=ErrorCode.E_EXEC_005,
            message=(
                f"Payload size {byte_count} bytes exceeds the maximum "
                f"allowed limit of {_MAX_PAYLOAD_BYTES} bytes."
            ),
            recoverable=True,
            trace_id=trace_id,
            timestamp=_get_timestamp(),
        )

    return None


def _check_privacy_coherence(
    request: InvocationRequest,
    trace_id: str,
) -> Optional[ErrorDetail]:
    """
    Reject structurally incoherent privacy / task_type combinations.

    Rule: If privacy_level == "local", any task type that requires network
    access must be rejected immediately, before execution begins.

    This is a structural enforcement check, not a routing decision.
    The Client is responsible for choosing the route; this gate refuses
    to execute a network-dependent task when local privacy is mandated.

    Returns:
        ErrorDetail with E-EXEC-004 if the combination is forbidden, else None.
    """
    if (
        request.privacy_level == PrivacyLevel.LOCAL
        and request.task_type in _NETWORK_DEPENDENT_TASK_TYPES
    ):
        return ErrorDetail(
            code=ErrorCode.E_EXEC_004,
            message=(
                f"Task type '{request.task_type}' requires network access "
                "but privacy_level is 'local'. Execution blocked."
            ),
            recoverable=False,
            trace_id=trace_id,
            timestamp=_get_timestamp(),
        )

    return None


def check_constraints(
    request: InvocationRequest,
    trace_id: str,
) -> Optional[ErrorDetail]:
    """
    Enforce all structural execution constraints for the given request.

    This is the single entry point for the EPIC2 enforcement gate.
    It runs each check in priority order and returns the first violation
    found, following the fail-fast policy from error-doctrine.md §4.

    This function is a pure function:
    - No I/O beyond returning a result.
    - No mutation of request or any shared state.
    - Deterministic: identical inputs always produce identical outputs.
    - Concurrency-safe: holds no mutable instance state.

    Args:
        request: The validated InvocationRequest to check.
        trace_id: The Execution Layer-generated trace identifier for this
                  invocation (generated before constraint checking begins).

    Returns:
        None if all constraints pass and execution may proceed.
        ErrorDetail describing the first constraint violation if one is found.
    """
    checks = [
        _check_payload_size,
        _check_privacy_coherence,
    ]

    for check in checks:
        error = check(request, trace_id)
        if error is not None:
            return error

    return None

