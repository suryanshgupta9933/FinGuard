"""
finguard.audit.backends.otel
============================
OpenTelemetry backend for FinGuard GuardTrace.

Emits standard W3C traces and metrics for DataDog, Honeycomb, Jaeger ingestion.
"""
import logging
from finguard.audit.backends.base import AuditBackend
from finguard.audit.trace import GuardTrace

logger = logging.getLogger("finguard.audit.otel")

try:
    from opentelemetry import trace, metrics
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


class OTELBackend(AuditBackend):
    """
    Submits GuardTraces via OpenTelemetry python SDK.
    """
    
    def __init__(self, **kwargs):
        if not OTEL_AVAILABLE:
            raise ImportError("OpenTelemetry is not installed. Install with `pip install finguard[observability]`")
        
        self.tracer = trace.get_tracer("finguard")
        self.meter = metrics.get_meter("finguard")
        
        # Setup metrics
        self.latency_histogram = self.meter.create_histogram(
            "finguard.latency.ms",
            description="End-to-end FinGuard evaluation latency in ms"
        )
        self.violation_counter = self.meter.create_counter(
            "finguard.violations.count",
            description="Count of policy blocks/violations by scanner"
        )
        
        logger.info("OpenTelemetry OTELBackend initialized.")

    def emit(self, trace_record: GuardTrace) -> None:
        if not OTEL_AVAILABLE:
            return
            
        try:
            # Generate common OTEL attributes
            attributes = {
                "finguard.policy_id": trace_record.policy_id,
                "finguard.risk_tier": trace_record.risk_tier,
                "finguard.action": trace_record.action,
                "finguard.is_safe": trace_record.is_safe,
            }
            
            # Attach safe metadata fields (e.g. session_id)
            for k, v in trace_record.metadata.items():
                attributes[f"finguard.meta.{k}"] = str(v)

            # ── 1. Emit sync metrics ──────────────────────────────────────────
            metric_tags = {"policy_id": trace_record.policy_id}
            self.latency_histogram.record(trace_record.total_latency_ms, metric_tags)
            
            if not trace_record.is_safe:
                for scanner in trace_record.input_scanners + trace_record.output_scanners:
                    if scanner.triggered:
                        self.violation_counter.add(1, {
                            "policy_id": trace_record.policy_id,
                            "scanner": scanner.scanner
                        })

            # ── 2. Emit Span Trace ───────────────────────────────────────────
            with self.tracer.start_as_current_span("finguard.guard", attributes=attributes) as span:
                
                # If block, mark the OTEL span status as an error explicitly 
                # so it lights up red in APM dashboards (DataDog, Jaeger)
                if not trace_record.is_safe:
                    span.set_status(Status(StatusCode.ERROR))
                    span.record_exception(ValueError(f"Blocked at {trace_record.block_stage} stage"))
                else:
                    span.set_status(Status(StatusCode.OK))
                    
                # We could create child spans for every scanner here, but 
                # a simpler implementation attaches them as span events.
                for scanner in trace_record.input_scanners + trace_record.output_scanners:
                    span.add_event(
                        name=f"finguard.scanner.{scanner.scanner}",
                        attributes={
                            "triggered": scanner.triggered,
                            "latency_ms": scanner.latency_ms,
                            "skipped": scanner.skipped,
                            "score": float(scanner.score) if scanner.score else 0.0
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Failed to emit trace to OTEL: {e}")
