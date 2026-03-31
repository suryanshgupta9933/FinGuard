"""
finguard.audit.backends.langfuse
================================
Native Langfuse backend for FinGuard GuardTrace.

Emits traces to Langfuse using the hierarchical API to support visual
session tracing and automatic safety score grouping.
"""
import os
import logging
from typing import Optional

from finguard.audit.backends.base import AuditBackend
from finguard.audit.trace import GuardTrace

logger = logging.getLogger("finguard.audit.langfuse")

try:
    from langfuse import Langfuse
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


class LangfuseBackend(AuditBackend):
    """
    Submits GuardTraces directly to Langfuse.
    
    If 'parent_observation_id' is passed in Trace metadata, this acts as a Span
    living inside a wider Agent/LLM trace. Otherwise it creates a standalone Trace.
    """
    
    def __init__(self, **kwargs):
        if not LANGFUSE_AVAILABLE:
            raise ImportError("Langfuse is not installed. Install with `pip install finguard[observability]`")
        
        # Will pick up standard LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST from env
        try:
            self.client = Langfuse()
            logger.info("LangfuseBackend initialized.")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse client: {e}")
            self.client = None

    def emit(self, trace: GuardTrace) -> None:
        if not self.client:
            return
            
        try:
            # ── 1. Grouping and metadata ──────────────────────────────
            session_id = trace.metadata.get("session_id")
            user_id = trace.metadata.get("user_id")
            tags = [f"policy:{trace.policy_id}", f"tier:{trace.risk_tier}"]
            if not trace.is_safe:
                tags.append("blocked")
                
            # If the orchestrator tells us we are part of an observation
            parent_id = trace.metadata.get("parent_observation_id")
            trace_id = trace.metadata.get("trace_id") or trace.trace_id

            # ── 2. Create Trace or Span ────────────────────────────────
            if parent_id:
                obs = self.client.span(
                    id=trace.trace_id,
                    trace_id=trace_id,
                    parent_observation_id=parent_id,
                    name="finguard_safety_check",
                    start_time=trace.timestamp,
                    metadata=trace.to_log_dict(),
                    input={"hash": trace.input_hash, "length": trace.input_length},
                )
            else:
                obs = self.client.trace(
                    id=trace.trace_id,
                    name="finguard_standalone_check",
                    session_id=session_id,
                    user_id=user_id,
                    tags=tags,
                    metadata=trace.to_log_dict()
                )

            # ── 3. Attach standard overall boolean score ───────────────
            # Score 1 if safe, 0 if blocked, mapped so analysts can filter easily
            self.client.score(
                trace_id=trace_id,
                observation_id=trace.trace_id if parent_id else None,
                name="finguard.is_safe",
                value=1.0 if trace.is_safe else 0.0,
                comment=f"Action taken: {trace.action}"
            )

            # ── 4. Attach detailed scores for violations ───────────────
            # e.g., prompt_injection = 1.0
            triggered = [s for s in trace.input_scanners + trace.output_scanners if s.triggered]
             
            for t_scan in triggered:
                self.client.score(
                    trace_id=trace_id,
                    observation_id=trace.trace_id if parent_id else None,
                    name=f"finguard.{t_scan.scanner}",
                    value=t_scan.score if t_scan.score is not None else 1.0,
                    comment="Violation detected",
                )

            self.client.flush()

        except Exception as e:
            # Observability shouldn't crash the main pipeline
            logger.error(f"Failed to emit trace to Langfuse: {e}")
