import functools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional
from .config import PolicyConfig
from .pipeline import InputPipeline, OutputPipeline
from .audit import AuditLogger

@dataclass
class GuardRequest:
    prompt: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GuardResult:
    output: Optional[str]
    is_safe: bool
    violations: List[Dict[str, Any]]
    action: str
    latency_ms: float = 0.0

class FinGuard:
    def __init__(self, policy: str | dict | PolicyConfig = "default"):
        self.policy = PolicyConfig.load(policy)
        self.input_pipe = InputPipeline(self.policy)
        self.output_pipe = OutputPipeline(self.policy)
        self.audit = AuditLogger(self.policy.audit)

    async def __call__(self, req: GuardRequest, llm_fn: Callable[[str], Coroutine[Any, Any, str]]) -> GuardResult:
        start_time = time.time()
        
        # Stage 1: parallel input checks
        safe, violations = await self.input_pipe.run(req)
        if not safe:
            latency = (time.time() - start_time) * 1000
            return self.audit.record(req, action="block", violations=violations, output=None, latency_ms=latency)

        # Call bounded LLM
        output = await llm_fn(req.prompt)

        # Stage 2: parallel output checks
        safe, violations = await self.output_pipe.run(output, req)
        
        # Policy-driven failure action
        action = "pass" if safe else (self.policy.output.on_fail if self.policy.output else "block")
        
        latency = (time.time() - start_time) * 1000
        return self.audit.record(req, action=action, violations=violations, output=output, latency_ms=latency)

    def wrap(self, llm_fn: Callable[[str], Coroutine[Any, Any, str]]):
        """Decorator for easy injection of FinGuard"""
        @functools.wraps(llm_fn)
        async def wrapper(prompt: str, *args, **kwargs) -> str:
            req = GuardRequest(prompt=prompt, metadata=kwargs)
            
            # Note: inside wrap, the llm_fn is called with prompt, args, kwargs
            async def bound_llm(p: str) -> str:
                return await llm_fn(p, *args, **kwargs)
                
            res = await self(req, bound_llm)
            
            if not res.is_safe and res.action == "block":
                raise ValueError(f"Blocked by FinGuard: {res.violations}")
            
            return res.output or ""

        return wrapper
