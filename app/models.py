"""
Data models for Invocation Boundary.

InvocationRequest: incoming request from orchestration layer
InvocationResponse: structured response with result or error
ErrorDetail: structured error information
"""

from enum import Enum
from typing import Any, Optional
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


class RouteStatus(str, Enum):
    """Route planning status values."""
    PLANNED = "planned"


class ErrorCode(str, Enum):
    """Execution-layer error codes."""
    E_EXEC_001 = "E-EXEC-001"  # UnsupportedTask
    E_EXEC_002 = "E-EXEC-002"  # ValidationError
    E_EXEC_003 = "E-EXEC-003"  # ExecutionFailure
    E_EXEC_004 = "E-EXEC-004"  # PrivacyViolation
    E_EXEC_005 = "E-EXEC-005"  # PayloadTooLarge


class EvidenceAttachment(BaseModel):
    """
    Evidence attachment for response source reference.

    Provides human-readable source information for result traceability.

    Attributes:
        source_id: Unique source identifier (e.g., "doc-001#p3")
        source_type: Source type (e.g., "pdf", "web", "note")
        location: Page number or section info (e.g., "p.3", "§2.1")
        snippet: Human-readable excerpt from source
        score: Optional relevance score (0.0-1.0)
    """
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(..., description="Unique source identifier")
    source_type: str = Field(..., description="Source type (pdf, web, note, etc.)")
    location: str = Field(..., description="Page or section location")
    snippet: str = Field(..., description="Human-readable text excerpt")
    score: Optional[float] = Field(None, description="Optional relevance score (0.0-1.0)")


class ErrorDetail(BaseModel):
    """
    Structured error information.

    Attributes:
        code: Error code (E-EXEC-001, E-EXEC-002, etc.)
        message: Human-readable error message
        recoverable: Whether retry might succeed
        trace_id: Execution Layer-generated trace identifier
        timestamp: Error occurrence time
    """
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    recoverable: bool = Field(..., description="Whether retry might succeed")
    trace_id: str = Field(..., description="Execution Layer-generated trace identifier (UUID)")
    timestamp: str = Field(..., description="Error timestamp (ISO-8601)")


class InvocationRequest(BaseModel):
    """
    Request payload for stateless task execution.

    Attributes:
        session_id: Unique identifier for tracking request lineage
        request_id: Unique request identifier (UUID)
        task_type: Type of task to execute (e.g., "echo", "transform")
        payload: Task-specific data
        timestamp: Client submission time hint (ISO-8601, optional)
        privacy_level: Privacy constraint (local, hybrid, cloud)
    """
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Unique session identifier")
    request_id: str = Field(..., description="Unique request identifier (UUID)")
    task_type: str = Field(..., description="Task type to execute")
    payload: dict = Field(default_factory=dict, description="Task-specific payload")
    timestamp: Optional[str] = Field(None, description="Client submission time hint (ISO-8601, optional)")
    privacy_level: Optional[PrivacyLevel] = Field(None, description="Privacy constraint")


class InvocationResponse(BaseModel):
    """
    Response from task execution.

    Attributes:
        session_id: Echo of request session_id for correlation
        request_id: Echo of request request_id for correlation
        trace_id: Execution Layer-generated trace identifier (UUID)
        status: Execution status (success or error)
        result: Result data if successful
        error: Structured error detail if failed
        timestamp: Response generation time (ISO-8601)
        execution_time_ms: Execution duration in milliseconds
        evidence: Evidence attachments for result (source references)
    """
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(..., description="Session identifier from request")
    request_id: str = Field(..., description="Request identifier from request")
    trace_id: str = Field(..., description="Execution Layer-generated trace identifier (UUID)")
    status: ExecutionStatus = Field(..., description="Execution status")
    result: dict = Field(default_factory=dict, description="Result data")
    error: Optional[ErrorDetail] = Field(None, description="Error detail if failed")
    timestamp: str = Field(..., description="Response generation time (ISO-8601)")
    execution_time_ms: int = Field(..., description="Execution duration in milliseconds")
    evidence: list[EvidenceAttachment] = Field(default_factory=list, description="Evidence attachments for the result")


class RouteRequest(BaseModel):
    """
    Request payload for Route Contract v0 planning.

    This schema is intentionally small and forward-compatible. The endpoint
    returns a typed route decision but does not execute the selected route.
    """
    model_config = ConfigDict(extra="allow")

    intent: str = Field(..., description="Caller intent for route planning")
    input: str | dict[str, Any] = Field(..., description="Input text or structured object to route")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    request_id: Optional[str] = Field(None, description="Optional caller request identifier")
    available_models: Optional[list[str]] = Field(None, description="Optional model candidates")
    available_tools: Optional[list[str]] = Field(None, description="Optional tool candidates")
    context: Optional[dict[str, Any]] = Field(None, description="Optional routing context")
    metadata: Optional[dict[str, Any]] = Field(None, description="Optional caller metadata")


class RouteResponse(BaseModel):
    """
    Response payload for Route Contract v0 planning.

    The response is governance metadata for a planned route only. No model,
    tool, or autonomous action is executed by this contract stub.
    """
    model_config = ConfigDict(extra="forbid")

    route: str = Field(..., description="Selected route identifier")
    reason: str = Field(..., description="Human-readable route decision reason")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Decision confidence from 0.0 to 1.0")
    requires_approval: bool = Field(..., description="Whether approval is required before execution")
    approval_reason: Optional[str] = Field(None, description="Reason approval is required, if any")
    audit_id: str = Field(..., description="Audit identifier for this route decision")
    trace_id: str = Field(..., description="Trace identifier for observability")
    request_id: str = Field(..., description="Caller request identifier or generated UUID")
    status: RouteStatus = Field(..., description="Route status; planned means not executed")
