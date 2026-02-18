"""
Data models for Invocation Boundary.

InvocationRequest: incoming request from orchestration layer
InvocationResponse: structured response with result or error
"""

from typing import Optional
from pydantic import BaseModel, Field


class InvocationRequest(BaseModel):
    """
    Request payload for stateless task execution.

    Attributes:
        session_id: Unique identifier for tracking request lineage
        task_type: Type of task to execute (e.g., "echo", "transform")
        payload: Task-specific data
    """
    session_id: str = Field(..., description="Unique session identifier")
    task_type: str = Field(..., description="Task type to execute")
    payload: dict = Field(default_factory=dict, description="Task-specific payload")


class InvocationResponse(BaseModel):
    """
    Response from task execution.

    Attributes:
        session_id: Echo of request session_id for correlation
        status: Execution status ("success" or "error")
        result: Result data if successful
        error: Error message if status is "error"
    """
    session_id: str = Field(..., description="Session identifier from request")
    status: str = Field(..., description="Execution status: 'success' or 'error'")
    result: dict = Field(default_factory=dict, description="Result data")
    error: Optional[str] = Field(None, description="Error message if failed")
