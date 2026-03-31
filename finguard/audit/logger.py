"""
finguard.audit.logger
======================
AuditLogger — assembles GuardTrace objects and dispatches them to backends.

Design decisions:

1. Scanner-to-name mapping lives here, not in scanners themselves.
   Scanners are third-party objects (llm-guard, presidio). We can't control
   their naming. The logger uses isinstance/type checks + a name registry
   to produce stable, human-readable scanner names for traces.

2. Multi-backend fan-out: a single logger can emit to multiple backends
   simultaneously (e.g. MemoryBackend for local queries + FileBackend for SIEM).
   This enables "warm" in-process trace access alongside durable logging.

3. Metadata filtering: AuditConfig.include_metadata_keys is an allowlist.
   Only declared keys flow into the trace's metadata dict. This prevents
   accidental PII leakage through the caller's metadata dict. Default: all
   keys are allowed if not configured, to avoid breaking existing integrations.
"""
from typing import Any, Dict, List, Optional
from .trace import GuardTrace, ScannerTrace
from .backends.base import AuditBackend
from .backends.memory import MemoryBackend


class AuditLogger:
    """
    Assembles GuardTrace from pipeline execution data and routes to backends.
    
    One AuditLogger instance per FinGuard instance, shared across calls.
    """

    def __init__(self, config=None):
        self.config = config
        self._backends: List[AuditBackend] = []
        self._memory: Optional[MemoryBackend] = None

        # Always attach memory backend — zero cost, powers in-process queries
        self._memory = MemoryBackend(maxlen=1000)
        self._backends.append(self._memory)

        # Attach additional backends from config
        if config:
            backend_type = getattr(config, "backend", "memory")
            if backend_type == "file":
                from .backends.file import FileBackend
                path = getattr(config, "file_path", "logs/finguard_%Y-%m-%d.ndjson")
                self._backends.append(FileBackend(path=path))
            elif backend_type == "console":
                self._backends.append(_ConsoleBackend())
            elif backend_type == "langfuse":
                from .backends.langfuse import LangfuseBackend
                self._backends.append(LangfuseBackend())
            elif backend_type == "otel":
                from .backends.otel import OTELBackend
                self._backends.append(OTELBackend())

    # ── Core record method (called by core.py) ─────────────────────────────

    def record(
        self,
        req: Any,
        action: str,
        violations: List[Dict[str, Any]],
        output: Optional[str] = None,
        latency_ms: float = 0.0,
        component_latencies: Dict[str, float] = None,
        input_scanner_traces: Optional[List[ScannerTrace]] = None,
        output_scanner_traces: Optional[List[ScannerTrace]] = None,
    ) -> Any:
        """
        Build a GuardResult + GuardTrace for this invocation and emit
        the trace to all configured backends.
        """
        from ..schema import GuardResult

        is_safe = action == "pass"

        # Determine where a block occurred
        block_stage = None
        if not is_safe:
            inp_triggered = any(
                s.triggered for s in (input_scanner_traces or [])
            )
            block_stage = "input" if inp_triggered else "output"

        # Resolve policy info from config
        policy_id = getattr(self.config, "__policy_id__", "unknown")
        policy_version = getattr(self.config, "__policy_version__", "0.0")
        risk_tier = getattr(self.config, "__risk_tier__", 1)

        # Build filtered metadata (allowlist-driven)
        raw_meta = getattr(req, "metadata", {}) or {}
        allowed_keys = getattr(
            self.config, "include_metadata_keys", None
        )
        if allowed_keys:
            filtered_meta = {k: v for k, v in raw_meta.items() if k in allowed_keys}
        else:
            filtered_meta = raw_meta

        redact = getattr(self.config, "redact_input", True)
        input_text = req.prompt if hasattr(req, "prompt") else ""

        trace = GuardTrace(
            policy_id=policy_id,
            policy_version=policy_version,
            risk_tier=risk_tier,
            input_hash=(
                GuardTrace.fingerprint(input_text) if redact else input_text[:50]
            ),
            input_length=len(input_text),
            input_scanners=input_scanner_traces or [],
            output_scanners=output_scanner_traces or [],
            is_safe=is_safe,
            action=action,
            block_stage=block_stage,
            total_latency_ms=latency_ms,
            metadata=filtered_meta,
        )

        # Emit to all backends
        for backend in self._backends:
            try:
                backend.emit(trace)
            except Exception:
                pass  # Never let a logging failure crash the guard

        # Developer-facing console print (only when console backend is active)
        if getattr(self.config, "backend", "memory") in ("console", "json"):
            print(f"\n{trace.summary()}")
            if component_latencies:
                lats = ", ".join(
                    f"{k}: {v:.1f}ms" for k, v in component_latencies.items()
                )
                print(f"  Scanners: {lats}")

        result = GuardResult(
            output=output,
            is_safe=is_safe,
            violations=violations,
            action=action,
            latency_ms=latency_ms,
            component_latencies=component_latencies or {},
            trace=trace,
        )
        return result

    def record_tool(self, tool_name: str, result: Any, metadata: Dict[str, Any]) -> GuardTrace:
        """Assembles and emits a GuardTrace specifically for a tool execution."""
        from .trace import GuardTrace, ScannerTrace
        
        st = ScannerTrace(
            scanner="tool_call_guard",
            stage="tool",
            triggered=not result.is_safe,
            score=1.0 if not result.is_safe else 0.0,
            violations=[{"reason": result.block_reason}] if not result.is_safe else [],
            latency_ms=result.latency_ms
        )
        
        policy_id = getattr(self.config, "__policy_id__", "unknown")
        policy_version = getattr(self.config, "__policy_version__", "0.0")
        risk_tier = getattr(self.config, "__risk_tier__", 1)

        allowed_keys = getattr(self.config, "include_metadata_keys", None)
        filtered_meta = {k: v for k, v in metadata.items() if k in allowed_keys} if allowed_keys else metadata

        trace = GuardTrace(
            policy_id=policy_id,
            policy_version=policy_version,
            risk_tier=max(risk_tier, result.risk_tier),
            input_hash="",
            input_length=0,
            input_scanners=[st],
            is_safe=result.is_safe,
            action=result.action,
            block_stage="tool" if not result.is_safe else None,
            total_latency_ms=result.latency_ms,
            metadata=filtered_meta,
        )

        for backend in self._backends:
            try:
                backend.emit(trace)
            except Exception:
                pass
                
        return trace

    # ── In-process query helpers ───────────────────────────────────────────

    @property
    def traces(self) -> List[GuardTrace]:
        """All traces in the in-memory buffer (most recent first)."""
        return list(reversed(self._memory.get_all()))

    def get_trace(self, trace_id: str) -> Optional[GuardTrace]:
        return self._memory.get_by_id(trace_id)

    def get_violations(self) -> List[GuardTrace]:
        """All blocked/flagged traces — quick access for incident review."""
        return self._memory.get_violations()

    def flush(self) -> None:
        for backend in self._backends:
            backend.flush()


class _ConsoleBackend(AuditBackend):
    """Prints the full JSON trace to stdout. Useful for local debugging."""
    import json

    def emit(self, trace: GuardTrace) -> None:
        import json
        print(json.dumps(trace.to_log_dict(), indent=2, ensure_ascii=False))
