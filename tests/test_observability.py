"""
tests/test_observability.py
===========================
Verifies that the Langfuse and OpenTelemetry backends correctly translate
FinGuard GuardTrace objects into spans, metrics, and scores.

Uses mocking to avoid requiring real API keys or running collector agents.
"""
import pytest
import sys
from unittest.mock import MagicMock, patch

from finguard.audit.trace import GuardTrace, ScannerTrace
from finguard.audit.backends.langfuse import LangfuseBackend, LANGFUSE_AVAILABLE
from finguard.audit.backends.otel import OTELBackend, OTEL_AVAILABLE

# Example trace for testing
@pytest.fixture
def sample_trace():
    return GuardTrace(
        trace_id="test-uuid-123",
        policy_id="test_policy",
        risk_tier=2,
        input_hash="deadbeef",
        input_length=100,
        is_safe=False,
        action="block",
        block_stage="input",
        total_latency_ms=45.0,
        metadata={"session_id": "sess_001", "user_id": "usr_99"},
        input_scanners=[
            ScannerTrace(scanner="presidio_pii", stage="input", triggered=True, score=0.99, latency_ms=10.0),
            ScannerTrace(scanner="injection", stage="input", triggered=False, latency_ms=35.0)
        ]
    )


@pytest.mark.skipif(not LANGFUSE_AVAILABLE, reason="langfuse not installed")
@patch("finguard.audit.backends.langfuse.Langfuse")
def test_langfuse_backend_emits_trace_and_scores(MockLangfuse, sample_trace):
    # Setup mock client
    mock_client = MagicMock()
    MockLangfuse.return_value = mock_client
    
    backend = LangfuseBackend()
    backend.client = mock_client  # Force use mock
    
    # Act
    backend.emit(sample_trace)
    
    # Assert Trace was created
    mock_client.trace.assert_called_once()
    trace_call_kwargs = mock_client.trace.call_args.kwargs
    assert trace_call_kwargs["name"] == "finguard_standalone_check"
    assert trace_call_kwargs["session_id"] == "sess_001"
    assert trace_call_kwargs["user_id"] == "usr_99"
    assert "blocked" in trace_call_kwargs["tags"]
    
    # Assert Scores were attached (1 for is_safe, 1 for the triggered scanner)
    assert mock_client.score.call_count == 2
    
    score_calls = mock_client.score.call_args_list
    # First score: finguard.is_safe = 0.0 (since is_safe=False)
    assert score_calls[0].kwargs["name"] == "finguard.is_safe"
    assert score_calls[0].kwargs["value"] == 0.0
    
    # Second score: finguard.presidio_pii = 0.99 (the triggered scanner)
    assert score_calls[1].kwargs["name"] == "finguard.presidio_pii"
    assert score_calls[1].kwargs["value"] == 0.99


@pytest.mark.skipif(not OTEL_AVAILABLE, reason="opentelemetry not installed")
@patch("finguard.audit.backends.otel.trace")
@patch("finguard.audit.backends.otel.metrics")
def test_otel_backend_emits_spans_and_metrics(mock_metrics, mock_trace, sample_trace):
    # Setup mock OTEL objects
    mock_tracer = MagicMock()
    mock_meter = MagicMock()
    mock_trace.get_tracer.return_value = mock_tracer
    mock_metrics.get_meter.return_value = mock_meter
    
    backend = OTELBackend()
    
    # Act
    backend.emit(sample_trace)
    
    # Assert Metrics: Histogram (latency) and Counter (violations)
    backend.latency_histogram.record.assert_called_once_with(
        45.0, {"policy_id": "test_policy"}
    )
    backend.violation_counter.add.assert_called_once_with(
        1, {"policy_id": "test_policy", "scanner": "presidio_pii"}
    )
    
    # Assert Trace Span
    mock_tracer.start_as_current_span.assert_called_once()
    span_call_kwargs = mock_tracer.start_as_current_span.call_args.kwargs
    assert span_call_kwargs["attributes"]["finguard.policy_id"] == "test_policy"
    assert span_call_kwargs["attributes"]["finguard.meta.session_id"] == "sess_001"
    
    # Inside the span context, assert status and events (scanners)
    mock_span = mock_tracer.start_as_current_span.return_value.__enter__.return_value
    assert mock_span.set_status.call_count == 1  # Should be set to Error
    assert mock_span.add_event.call_count == 2   # 2 scanners = 2 events
