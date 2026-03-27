import functools
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union
from .config import PolicyConfig
from .pipeline import InputPipeline, OutputPipeline
from .audit import AuditLogger
from .schema import GuardRequest, GuardResult, ValidationResult
from .router import get_vault
from .utils import check_runtime_health, download_models

class FinGuard:
    @staticmethod
    def download_models():
        """Pre-fetch all models for built-in policies."""
        download_models()

    def __init__(self, policy: str | dict | PolicyConfig = "default"):
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
        self.audit = AuditLogger(self.policy.audit)

    async def __call__(self, 
                       input_data: Union[str, GuardRequest], 
                       llm_fn: Callable[[str], Coroutine[Any, Any, str]]) -> GuardResult:
        """
        Main execution entry point. Accepts a raw string or a GuardRequest.
        """
        start_time = time.perf_counter() # Use high-precision timer
        
        # Polymorphic input handling
        if isinstance(input_data, str):
            req = GuardRequest(prompt=input_data)
        else:
            req = input_data

        all_violations = []
        all_latencies = {}
        
        # Stage 1: input checks
        safe, violations, in_lats = await self.input_pipe.run(req)
        all_violations.extend(violations)
        all_latencies.update(in_lats)
        
        if not safe:
            latency = (time.perf_counter() - start_time) * 1000
            return self.audit.record(req, action="block", violations=all_violations, 
                                     output=None, latency_ms=latency, 
                                     component_latencies=all_latencies)

        # Call bounded LLM
        output = await llm_fn(req.prompt)

        # Stage 2: output checks (Includes possible redaction)
        safe, violations, out_lats, sanitized_output = await self.output_pipe.run(output, req)
        all_violations.extend(violations)
        all_latencies.update(out_lats)
        
        # Policy-driven failure action
        action = "pass" if safe else (self.policy.output.on_fail if self.policy.output else "block")
        
        latency = (time.perf_counter() - start_time) * 1000
        return self.audit.record(req, action=action, violations=all_violations, 
                                 output=sanitized_output, latency_ms=latency,
                                 component_latencies=all_latencies)

    def wrap(self, llm_fn: Callable[[str], Coroutine[Any, Any, str]]):
        """Decorator for easy injection of FinGuard"""
        @functools.wraps(llm_fn)
        async def wrapper(prompt: str, *args, **kwargs) -> str:
            req = GuardRequest(prompt=prompt, metadata=kwargs)
            
            async def bound_llm(p: str) -> str:
                return await llm_fn(p, *args, **kwargs)
                
            res = await self(req, bound_llm)
            
            if not res.is_safe and res.action == "block":
                raise ValueError(f"Blocked by FinGuard: {res.violations}")
            
            return res.output or ""

        return wrapper
