"""
Constrained task executor.

Pure execution logic with no routing or decision-making.
Each task type is handled deterministically.
"""

from app.models import InvocationRequest, InvocationResponse


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
    task_type = request.task_type
    session_id = request.session_id
    payload = request.payload

    if task_type == "echo":
        return InvocationResponse(
            session_id=session_id,
            status="success",
            result=payload,
            error=None
        )

    # Unsupported task type
    return InvocationResponse(
        session_id=session_id,
        status="error",
        result={},
        error="unsupported_task"
    )
