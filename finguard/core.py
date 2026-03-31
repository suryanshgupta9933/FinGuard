import functools
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

from .config import PolicyConfig
from .pipeline import InputPipeline, OutputPipeline
from .audit import AuditLogger, GuardTrace, ScannerTrace
from .schema import GuardRequest, GuardResult, ValidationResult
from .exceptions import FinGuardViolation, ToolCallViolation
from .router import get_vault
from .utils import check_runtime_health, download_models
from .tools.guard import ToolCallGuard
from .tools.schema import ToolCallRequest, ToolCallResult

# ── Risk tier mapping ─────────────────────────────────────────────────────────
_RISK_TIER = {"low": 1, "medium": 2, "high": 3}


class FinGuard:
    """
    FinGuard — LLM Safety Layer for Financial AI.
    
    v0.4 — Now emits a full GuardTrace for every invocation.
    Access traces via guard.traces, guard.get_trace(id), or guard.violations.
    """

    @staticmethod
    def download_models():
        """Pre-fetch all models for built-in policies."""
        download_models()

    def __init__(self, policy: Union[str, dict, PolicyConfig] = "default"):
        """
        Initialize FinGuard with a policy.
        Optimized for high-speed CPU inference (ONNX) by default.
        Uses cached models to ensure near-instant multi-instance initialization.
        """
        # Perform environment pre-flight check
        check_runtime_health()

        self.policy = PolicyConfig.load(policy)
        self.vault = get_vault()
        self.input_pipe = InputPipeline(self.policy, vault=self.vault)
        self.output_pipe = OutputPipeline(self.policy)

        # Inject policy context into AuditConfig so the logger can build rich traces
        audit_cfg = self.policy.audit
        if audit_cfg is not None:
            audit_cfg.__policy_id__ = self.policy.policy_id
            audit_cfg.__policy_version__ = getattr(self.policy, "version", "0.0")
            audit_cfg.__risk_tier__ = _RISK_TIER.get(self.policy.risk_level, 1)

        self.audit = AuditLogger(audit_cfg)
        self.tool_guard = ToolCallGuard(self.policy.tools)

    # ── Main execution entry point ────────────────────────────────────────────

    async def __call__(
        self,
        input_data: Union[str, GuardRequest],
        llm_fn: Callable[[str], Coroutine[Any, Any, str]],
    ) -> GuardResult:
        """
        Main execution entry point. Accepts a raw string or a GuardRequest.
        Returns GuardResult with attached GuardTrace.
        """
        start_time = time.perf_counter()

        # Polymorphic input handling
        req = GuardRequest(prompt=input_data) if isinstance(input_data, str) else input_data

        all_violations = []
        all_latencies = {}

        # Stage 1: Input checks
        safe, violations, in_lats, in_traces = await self.input_pipe.run(req)
        all_violations.extend(violations)
        all_latencies.update(in_lats)

        if not safe:
            latency = (time.perf_counter() - start_time) * 1000
            return self.audit.record(
                req,
                action="block",
                violations=all_violations,
                output=None,
                latency_ms=latency,
                component_latencies=all_latencies,
                input_scanner_traces=in_traces,
                output_scanner_traces=[],
            )

        # Call bounded LLM
        output = await llm_fn(req.prompt)

        # Stage 2: Output checks (includes possible redaction)
        safe, violations, out_lats, sanitized_output, out_traces = await self.output_pipe.run(
            output, req
        )
        all_violations.extend(violations)
        all_latencies.update(out_lats)

        action = "pass" if safe else (self.policy.output.on_fail if self.policy.output else "block")

        latency = (time.perf_counter() - start_time) * 1000
        return self.audit.record(
            req,
            action=action,
            violations=all_violations,
            output=sanitized_output,
            latency_ms=latency,
            component_latencies=all_latencies,
            input_scanner_traces=in_traces,
            output_scanner_traces=out_traces,
        )

    # ── Trace query API ───────────────────────────────────────────────────────

    @property
    def traces(self) -> List[GuardTrace]:
        """All traces from this FinGuard instance (most recent first)."""
        return self.audit.traces

    def get_trace(self, trace_id: str) -> Optional[GuardTrace]:
        """Retrieve a specific trace by its UUID."""
        return self.audit.get_trace(trace_id)

    @property
    def violations(self) -> List[GuardTrace]:
        """All traces where a block or violation occurred."""
        return self.audit.get_violations()

    # ── Tool Guarding API ─────────────────────────────────────────────────────

    async def guard_tool_call(self, tool_name: str, arguments: Dict[str, Any] = None, **kwargs) -> ToolCallResult:
        """
        Intercepts an agent tool execution and verifies it against the policy.
        Raises ToolCallViolation if the tool is blocked or rate-limited.
        """
        req = ToolCallRequest(tool_name=tool_name, arguments=arguments or {}, **kwargs)
        res = self.tool_guard.evaluate(req)
        
        trace = self.audit.record_tool(tool_name, res, kwargs)
        
        if not res.is_safe:
            raise ToolCallViolation(f"Blocked Tool Call '{tool_name}': {res.block_reason}", trace=trace)
            
        return res

    # ── Decorator ─────────────────────────────────────────────────────────────

    def wrap(self, llm_fn: Callable[[str], Coroutine[Any, Any, str]]):
        """Decorator for easy injection of FinGuard."""
        @functools.wraps(llm_fn)
        async def wrapper(prompt: str, *args, **kwargs) -> str:
            req = GuardRequest(prompt=prompt, metadata=kwargs)

            async def bound_llm(p: str) -> str:
                return await llm_fn(p, *args, **kwargs)

            res = await self(req, bound_llm)

            if not res.is_safe and res.action == "block":
                raise FinGuardViolation(f"Blocked by FinGuard: {res.violations}", trace=res.trace)

            return res.output or ""

        return wrapper
