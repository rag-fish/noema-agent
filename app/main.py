"""
noema-agent v2 — Minimal API

Stateless execution layer with a typed Route Contract v0 stub.
Accepts InvocationRequest, executes constrained task, returns InvocationResponse.
"""

import uuid

from fastapi import FastAPI

from app.executor import execute_task
from app.logging_utils import log_route_planned
from app.models import InvocationRequest, InvocationResponse, RouteRequest, RouteResponse, RouteStatus

app = FastAPI(
    title="noema-agent v2",
    description="Stateless execution layer for Noesis Noema architecture",
    version="3.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "noema-agent",
        "version": "3.0.0",
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


@app.post("/v1/route", response_model=RouteResponse)
async def route(request: RouteRequest) -> RouteResponse:
    """
    Route Contract v0 endpoint.

    Returns a typed route decision and governance metadata only.
    This v0 stub does not execute routes, call models, call tools, or start
    autonomous behavior.
    """
    trace_id = str(uuid.uuid4())
    audit_id = str(uuid.uuid4())
    request_id = request.request_id or str(uuid.uuid4())
    selected_route = "local_echo"
    status = RouteStatus.PLANNED

    response = RouteResponse(
        route=selected_route,
        reason=(
            "Route Contract v0 stub selected local_echo for typed planning only; "
            "no route was executed and no external model or tool was called."
        ),
        confidence=0.5,
        requires_approval=False,
        approval_reason=None,
        audit_id=audit_id,
        trace_id=trace_id,
        request_id=request_id,
        status=status,
    )

    log_route_planned(
        trace_id=trace_id,
        request_id=request_id,
        session_id=request.session_id,
        selected_route=selected_route,
        requires_approval=response.requires_approval,
        status=status.value,
    )

    return response


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "executor": "ready",
        "supported_tasks": ["echo"]
    }
