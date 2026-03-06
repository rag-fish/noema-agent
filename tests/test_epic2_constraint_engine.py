"""
Unit tests for EPIC2 — Constraint Engine.

Covers:
  - test_payload_within_limit_passes
  - test_payload_exceeds_limit_returns_E_EXEC_005
  - test_constraint_engine_stateless
  - test_constraint_rejected_event_logged

Design reference: docs/epic2-constraint-engine-alignment.md
"""

import json
import logging
import re
import uuid
from unittest.mock import patch

import pytest

from app.constraint_engine import (
    _DEFAULT_MAX_PAYLOAD_BYTES,
    _check_payload_size,
    _check_privacy_coherence,
    check_constraints,
)
from app.executor import execute_task
from app.models import (
    ErrorCode,
    ExecutionStatus,
    InvocationRequest,
    PrivacyLevel,
)

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _is_valid_uuid(value: str) -> bool:
    return bool(UUID_PATTERN.match(value))


def _make_request(**overrides) -> InvocationRequest:
    """Build a minimal valid InvocationRequest, with optional field overrides."""
    defaults = {
        "session_id": "session-test",
        "request_id": str(uuid.uuid4()),
        "task_type": "echo",
        "payload": {"message": "hello"},
    }
    defaults.update(overrides)
    return InvocationRequest(**defaults)


def _make_trace_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# check_constraints — payload size checks
# ---------------------------------------------------------------------------


class TestPayloadSizeCheck:
    def test_payload_within_limit_passes(self):
        """
        A payload well within the byte limit must not raise any constraint error.
        Satisfies: test_payload_within_limit_passes (alignment doc §8.6)
        """
        request = _make_request(payload={"key": "small value"})
        trace_id = _make_trace_id()

        result = _check_payload_size(request, trace_id)

        assert result is None

    def test_payload_at_exact_limit_passes(self):
        """A payload whose JSON encoding is exactly MAX bytes must pass."""
        # Build a value that fills the limit exactly.
        target_bytes = _DEFAULT_MAX_PAYLOAD_BYTES
        # '{"k": ""}' is 9 bytes; pad the value to hit the target exactly.
        filler_length = target_bytes - len(b'{"k": ""}')
        request = _make_request(payload={"k": "x" * filler_length})

        serialized_len = len(json.dumps(request.payload, ensure_ascii=False).encode("utf-8"))
        assert serialized_len == target_bytes

        result = _check_payload_size(request, _make_trace_id())
        assert result is None

    def test_payload_exceeds_limit_returns_E_EXEC_005(self):
        """
        A payload that exceeds MAX_PAYLOAD_BYTES must produce an E-EXEC-005 ErrorDetail.
        Satisfies: test_payload_exceeds_limit_returns_E_EXEC_005 (alignment doc §8.6)
        """
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(payload={"data": oversized_value})
        trace_id = _make_trace_id()

        result = _check_payload_size(request, trace_id)

        assert result is not None
        assert result.code == ErrorCode.E_EXEC_005
        assert result.trace_id == trace_id
        assert result.recoverable is True
        assert "exceeds" in result.message.lower()

    def test_payload_exceeds_limit_error_contains_trace_id(self):
        """The returned ErrorDetail must carry the caller-supplied trace_id."""
        oversized_value = "y" * (_DEFAULT_MAX_PAYLOAD_BYTES + 100)
        request = _make_request(payload={"data": oversized_value})
        trace_id = _make_trace_id()

        result = _check_payload_size(request, trace_id)

        assert result is not None
        assert result.trace_id == trace_id

    def test_check_constraints_delegates_payload_size(self):
        """
        check_constraints must surface E-EXEC-005 for an oversized payload.
        Verifies the aggregation function routes to _check_payload_size.
        """
        oversized_value = "z" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(payload={"data": oversized_value})
        trace_id = _make_trace_id()

        result = check_constraints(request, trace_id)

        assert result is not None
        assert result.code == ErrorCode.E_EXEC_005


# ---------------------------------------------------------------------------
# check_constraints — privacy coherence checks
# ---------------------------------------------------------------------------


class TestPrivacyCoherenceCheck:
    def test_local_privacy_with_non_network_task_passes(self):
        """
        privacy_level=local with a task type not in _NETWORK_DEPENDENT_TASK_TYPES
        must pass (echo is not a network-dependent task).
        """
        request = _make_request(
            task_type="echo",
            privacy_level=PrivacyLevel.LOCAL,
            payload={"msg": "ok"},
        )
        result = _check_privacy_coherence(request, _make_trace_id())
        assert result is None

    def test_no_privacy_level_passes(self):
        """Absence of privacy_level must not trigger any constraint violation."""
        request = _make_request(privacy_level=None, payload={"msg": "ok"})
        result = _check_privacy_coherence(request, _make_trace_id())
        assert result is None

    def test_cloud_privacy_with_echo_passes(self):
        """privacy_level=cloud with echo task must pass."""
        request = _make_request(
            task_type="echo",
            privacy_level=PrivacyLevel.CLOUD,
            payload={"msg": "cloud test"},
        )
        result = _check_privacy_coherence(request, _make_trace_id())
        assert result is None

    def test_local_privacy_blocks_network_dependent_task(self):
        """
        If a task type is in _NETWORK_DEPENDENT_TASK_TYPES and privacy_level==local,
        an E-EXEC-004 error must be returned.

        We temporarily register a fake network task to exercise the rule without
        touching production task lists.
        """
        import app.constraint_engine as engine_module

        original = engine_module._NETWORK_DEPENDENT_TASK_TYPES
        try:
            engine_module._NETWORK_DEPENDENT_TASK_TYPES = frozenset({"cloud_search"})
            request = _make_request(
                task_type="cloud_search",
                privacy_level=PrivacyLevel.LOCAL,
                payload={},
            )
            trace_id = _make_trace_id()

            result = _check_privacy_coherence(request, trace_id)

            assert result is not None
            assert result.code == ErrorCode.E_EXEC_004
            assert result.recoverable is False
            assert result.trace_id == trace_id
        finally:
            engine_module._NETWORK_DEPENDENT_TASK_TYPES = original


# ---------------------------------------------------------------------------
# Statelessness guarantee
# ---------------------------------------------------------------------------


class TestConstraintEngineStateless:
    def test_constraint_engine_stateless(self):
        """
        Multiple sequential calls to check_constraints must produce independent
        results. No shared mutable state must accumulate between invocations.
        Satisfies: test_constraint_engine_stateless (alignment doc §8.6)
        """
        small_request = _make_request(payload={"k": "v"})
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        large_request = _make_request(payload={"data": oversized_value})

        trace_1 = _make_trace_id()
        trace_2 = _make_trace_id()
        trace_3 = _make_trace_id()

        # Pass → Fail → Pass must all produce independent, correct results.
        result_pass_1 = check_constraints(small_request, trace_1)
        result_fail = check_constraints(large_request, trace_2)
        result_pass_2 = check_constraints(small_request, trace_3)

        assert result_pass_1 is None
        assert result_fail is not None
        assert result_fail.code == ErrorCode.E_EXEC_005
        assert result_fail.trace_id == trace_2
        assert result_pass_2 is None

    def test_each_call_uses_supplied_trace_id(self):
        """Each call must stamp its own trace_id onto the returned error, not a cached one."""
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(payload={"data": oversized_value})

        trace_a = str(uuid.uuid4())
        trace_b = str(uuid.uuid4())

        error_a = check_constraints(request, trace_a)
        error_b = check_constraints(request, trace_b)

        assert error_a is not None
        assert error_b is not None
        assert error_a.trace_id == trace_a
        assert error_b.trace_id == trace_b
        assert error_a.trace_id != error_b.trace_id


# ---------------------------------------------------------------------------
# End-to-end: executor integration with constraint gate
# ---------------------------------------------------------------------------


class TestExecutorConstraintIntegration:
    def test_valid_request_not_blocked_by_constraint_engine(self):
        """A valid, small-payload echo request must not be rejected by the gate."""
        request = _make_request(
            task_type="echo",
            payload={"message": "valid"},
        )
        response = execute_task(request)

        assert response.status == ExecutionStatus.SUCCESS
        assert response.result == {"message": "valid"}
        assert response.error is None

    def test_oversized_payload_blocked_before_task_dispatch(self):
        """
        An oversized payload must be blocked by the constraint gate and must
        return E-EXEC-005, never reaching task dispatch logic.
        """
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(payload={"data": oversized_value})

        response = execute_task(request)

        assert response.status == ExecutionStatus.ERROR
        assert response.error is not None
        assert response.error.code == ErrorCode.E_EXEC_005
        assert _is_valid_uuid(response.trace_id)
        assert response.error.trace_id == response.trace_id
        assert response.result == {}
        assert response.evidence == []

    def test_oversized_payload_response_has_execution_time_ms(self):
        """Constraint-rejected responses must still include execution_time_ms."""
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(payload={"data": oversized_value})

        response = execute_task(request)

        assert isinstance(response.execution_time_ms, int)
        assert response.execution_time_ms >= 0

    def test_oversized_payload_echoes_session_and_request_ids(self):
        """session_id and request_id must be echoed even on constraint rejection."""
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(
            session_id="my-session",
            request_id="my-request",
            payload={"data": oversized_value},
        )
        response = execute_task(request)

        assert response.session_id == "my-session"
        assert response.request_id == "my-request"


# ---------------------------------------------------------------------------
# Logging: constraint_rejected event
# ---------------------------------------------------------------------------


class TestConstraintRejectedEventLogged:
    def test_constraint_rejected_event_logged(self):
        """
        When the constraint gate blocks a request, a constraint_rejected log
        event must be emitted with the required fields.
        Satisfies: test_constraint_rejected_event_logged (alignment doc §8.6)
        """
        oversized_value = "x" * (_DEFAULT_MAX_PAYLOAD_BYTES + 1)
        request = _make_request(
            session_id="log-session",
            request_id="log-request",
            task_type="echo",
            payload={"data": oversized_value},
        )

        emitted_events = []

        original_warning = logging.Logger.warning

        def capture_warning(self, msg, *args, **kwargs):
            emitted_events.append(msg)
            original_warning(self, msg, *args, **kwargs)

        with patch.object(logging.Logger, "warning", capture_warning):
            execute_task(request)

        # At least one constraint_rejected event must have been emitted.
        constraint_events = [
            e for e in emitted_events
            if '"event_name": "constraint_rejected"' in e
        ]
        assert len(constraint_events) >= 1, (
            "Expected at least one constraint_rejected log event, found none."
        )

        import json as json_module
        parsed = json_module.loads(constraint_events[0])

        assert parsed["event_name"] == "constraint_rejected"
        assert _is_valid_uuid(parsed["trace_id"])
        assert parsed["session_id"] == "log-session"
        assert parsed["request_id"] == "log-request"
        assert parsed["task_type"] == "echo"
        assert parsed["error_code"] == ErrorCode.E_EXEC_005.value
        assert "constraint_name" in parsed
        assert "timestamp" in parsed

    def test_constraint_rejected_log_does_not_contain_raw_payload(self):
        """
        The constraint_rejected log event must NOT contain raw payload content.
        Enforces observability-standard.md §6.1 redaction policy.
        """
        secret_content = "TOP_SECRET_PAYLOAD_CONTENT"
        oversized_value = secret_content * ((_DEFAULT_MAX_PAYLOAD_BYTES // len(secret_content)) + 2)
        request = _make_request(payload={"data": oversized_value})

        emitted_events = []

        original_warning = logging.Logger.warning

        def capture_warning(self, msg, *args, **kwargs):
            emitted_events.append(msg)
            original_warning(self, msg, *args, **kwargs)

        with patch.object(logging.Logger, "warning", capture_warning):
            execute_task(request)

        constraint_events = [
            e for e in emitted_events
            if '"event_name": "constraint_rejected"' in e
        ]
        for event_str in constraint_events:
            assert secret_content not in event_str, (
                "Raw payload content must not appear in constraint_rejected log events."
            )

