"""
noema-agent v2 — Minimal API

Stateless execution layer with no routing or persistence.
Accepts InvocationRequest, executes constrained task, returns InvocationResponse.
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.models import InvocationRequest, InvocationResponse
from app.executor import execute_task

app = FastAPI(
    title="noema-agent v2",
    description="Stateless execution layer for Noesis Noema architecture",
    version="2.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "noema-agent",
        "version": "2.0.0",
        "status": "ready",
        "description": "Stateless execution layer"
    }


@app.post("/invoke", response_model=InvocationResponse)
async def invoke(request: InvocationRequest) -> InvocationResponse:
    """
    Invocation Boundary endpoint.

    Accepts a constrained task execution request and returns structured response.
    No routing, no decision-making, no persistence.

    Args:
        request: InvocationRequest with session_id, task_type, and payload

    Returns:
        InvocationResponse with execution status and result
    """
    response = execute_task(request)
    return response


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "executor": "ready",
        "supported_tasks": ["echo"]
    }
