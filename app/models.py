"""
Data models for Invocation Boundary.

InvocationRequest: incoming request from orchestration layer
InvocationResponse: structured response with result or error
ErrorDetail: structured error information
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PrivacyLevel(str, Enum):
    """Privacy constraint levels for execution."""
    LOCAL = "local"
    HYBRID = "hybrid"
    CLOUD = "cloud"


class ExecutionStatus(str, Enum):
    """Execution status values."""
    SUCCESS = "success"
    ERROR = "error"


class ErrorCode(str, Enum):
    """Execution-layer error codes."""
    E_EXEC_001 = "E-EXEC-001"  # UnsupportedTask
    E_EXEC_002 = "E-EXEC-002"  # ValidationError
    E_EXEC_003 = "E-EXEC-003"  # ExecutionFailure
    E_EXEC_004 = "E-EXEC-004"  # PrivacyViolation
    E_EXEC_005 = "E-EXEC-005"  # PayloadTooLarge


class ErrorDetail(BaseModel):
    """
    Structured error information.

    Attributes:
        code: Error code (E-EXEC-001, E-EXEC-002, etc.)
        message: Human-readable error message
        recoverable: Whether retry might succeed
        trace_id: Distributed tracing identifier
        timestamp: Error occurrence time
    """
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    recoverable: bool = Field(..., description="Whether retry might succeed")
    trace_id: str = Field(..., description="Distributed tracing identifier")
    timestamp: str = Field(..., description="Error timestamp (ISO-8601)")


class InvocationRequest(BaseModel):
    """
    Request payload for stateless task execution.

    Attributes:
        session_id: Unique identifier for tracking request lineage
        request_id: Unique request identifier (UUID)
        task_type: Type of task to execute (e.g., "echo", "transform")
        payload: Task-specific data
        timestamp: Request creation time (ISO-8601)
        trace_id: Distributed tracing identifier (UUID)
        privacy_level: Privacy constraint (local, hybrid, cloud)
    """
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Unique session identifier")
    request_id: str = Field(..., description="Unique request identifier (UUID)")
    task_type: str = Field(..., description="Task type to execute")
    payload: dict = Field(default_factory=dict, description="Task-specific payload")
    timestamp: str = Field(..., description="Request creation time (ISO-8601)")
    trace_id: str = Field(..., description="Distributed tracing identifier (UUID)")
    privacy_level: Optional[PrivacyLevel] = Field(None, description="Privacy constraint")


class InvocationResponse(BaseModel):
    """
    Response from task execution.

    Attributes:
        session_id: Echo of request session_id for correlation
        request_id: Echo of request request_id for correlation
        trace_id: Echo of request trace_id for correlation
        status: Execution status (success or error)
        result: Result data if successful
        error: Structured error detail if failed
        timestamp: Response generation time (ISO-8601)
        execution_time_ms: Execution duration in milliseconds
    """
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Session identifier from request")
    request_id: str = Field(..., description="Request identifier from request")
    trace_id: str = Field(..., description="Trace identifier from request")
    status: ExecutionStatus = Field(..., description="Execution status")
    result: dict = Field(default_factory=dict, description="Result data")
    error: Optional[ErrorDetail] = Field(None, description="Error detail if failed")
    timestamp: str = Field(..., description="Response generation time (ISO-8601)")
    execution_time_ms: int = Field(..., description="Execution duration in milliseconds")
