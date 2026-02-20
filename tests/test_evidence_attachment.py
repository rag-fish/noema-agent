"""
Unit tests for X-4 Evidence Attachment.

Tests EvidenceAttachment model and evidence integration in responses.
Updated for X-5: trace_id removed from InvocationRequest.
"""

import re
import pytest
from app.models import (
    InvocationRequest,
    InvocationResponse,
    EvidenceAttachment,
    ExecutionStatus
)
from app.executor import execute_task

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE
)


def _is_valid_uuid(value: str) -> bool:
    return bool(UUID_PATTERN.match(value))


def test_evidence_attachment_valid():
    """Test valid EvidenceAttachment creation"""
    evidence = EvidenceAttachment(
        source_id="doc-001#p3",
        source_type="pdf",
        location="p.3",
        snippet="This is a human-readable excerpt from the source.",
        score=0.95
    )
    assert evidence.source_id == "doc-001#p3"
    assert evidence.source_type == "pdf"
    assert evidence.location == "p.3"
    assert evidence.snippet == "This is a human-readable excerpt from the source."
    assert evidence.score == 0.95


def test_evidence_attachment_optional_score():
    """Test EvidenceAttachment with optional score"""
    evidence = EvidenceAttachment(
        source_id="web-123",
        source_type="web",
        location="§2.1",
        snippet="Web content excerpt"
    )
    assert evidence.score is None


def test_evidence_attachment_rejects_extra_fields():
    """Test that extra fields are rejected"""
    with pytest.raises(Exception):
        EvidenceAttachment(
            source_id="doc-001",
            source_type="pdf",
            location="p.1",
            snippet="Text",
            extra_field="should_fail"
        )


def test_invocation_response_can_hold_evidence():
    """Test that InvocationResponse can hold evidence attachments"""
    evidence1 = EvidenceAttachment(
        source_id="doc-001#p3",
        source_type="pdf",
        location="p.3",
        snippet="First evidence snippet",
        score=0.95
    )
    evidence2 = EvidenceAttachment(
        source_id="doc-002#p7",
        source_type="pdf",
        location="p.7",
        snippet="Second evidence snippet",
        score=0.87
    )

    response = InvocationResponse(
        session_id="session-123",
        request_id="request-456",
        trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        status=ExecutionStatus.SUCCESS,
        result={"answer": "test"},
        error=None,
        timestamp="2026-02-21T10:00:00Z",
        execution_time_ms=50,
        evidence=[evidence1, evidence2]
    )

    assert len(response.evidence) == 2
    assert response.evidence[0].source_id == "doc-001#p3"
    assert response.evidence[1].source_id == "doc-002#p7"


def test_invocation_response_empty_evidence_by_default():
    """Test that InvocationResponse has empty evidence list by default"""
    response = InvocationResponse(
        session_id="session-123",
        request_id="request-456",
        trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        status=ExecutionStatus.SUCCESS,
        result={},
        error=None,
        timestamp="2026-02-21T10:00:00Z",
        execution_time_ms=50
    )

    assert response.evidence == []


def test_evidence_human_readable_snippet():
    """Test that snippet contains human-readable text"""
    evidence = EvidenceAttachment(
        source_id="doc-001",
        source_type="pdf",
        location="p.1",
        snippet="This is a human-readable text excerpt with normal characters."
    )

    # Verify snippet is not empty
    assert len(evidence.snippet) > 0

    # Verify snippet contains readable characters (basic check)
    assert evidence.snippet.strip() != ""
    assert any(c.isalnum() or c.isspace() for c in evidence.snippet)


def test_echo_task_passes_through_evidence():
    """Test that echo task passes through evidence from payload"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={
            "message": "test",
            "evidence": [
                {
                    "source_id": "doc-001#p3",
                    "source_type": "pdf",
                    "location": "p.3",
                    "snippet": "This is the evidence text",
                    "score": 0.92
                },
                {
                    "source_id": "doc-002#p5",
                    "source_type": "web",
                    "location": "§2.1",
                    "snippet": "Another evidence excerpt"
                }
            ]
        },
    )

    response = execute_task(request)

    assert response.status == ExecutionStatus.SUCCESS
    assert _is_valid_uuid(response.trace_id)
    assert len(response.evidence) == 2
    assert response.evidence[0].source_id == "doc-001#p3"
    assert response.evidence[0].snippet == "This is the evidence text"
    assert response.evidence[0].score == 0.92
    assert response.evidence[1].source_id == "doc-002#p5"
    assert response.evidence[1].snippet == "Another evidence excerpt"
    assert response.evidence[1].score is None


def test_echo_task_without_evidence():
    """Test that echo task works without evidence in payload"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={"message": "test without evidence"},
    )

    response = execute_task(request)

    assert response.status == ExecutionStatus.SUCCESS
    assert response.evidence == []


def test_echo_task_ignores_invalid_evidence():
    """Test that echo task ignores malformed evidence items"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="echo",
        payload={
            "message": "test",
            "evidence": [
                {
                    "source_id": "doc-001",
                    "source_type": "pdf",
                    "location": "p.1",
                    "snippet": "Valid evidence"
                },
                {
                    "invalid": "missing required fields"
                },
                {
                    "source_id": "doc-002",
                    "source_type": "web",
                    "location": "p.2",
                    "snippet": "Another valid evidence"
                }
            ]
        },
    )

    response = execute_task(request)

    # Should have 2 valid evidence items, skipping the invalid one
    assert response.status == ExecutionStatus.SUCCESS
    assert len(response.evidence) == 2
    assert response.evidence[0].source_id == "doc-001"
    assert response.evidence[1].source_id == "doc-002"


def test_error_response_has_empty_evidence():
    """Test that error responses have empty evidence list"""
    request = InvocationRequest(
        session_id="session-123",
        request_id="request-456",
        task_type="unsupported_task",
        payload={},
    )

    response = execute_task(request)

    assert response.status == ExecutionStatus.ERROR
    assert response.evidence == []
    assert _is_valid_uuid(response.trace_id)
    assert response.error.trace_id == response.trace_id

