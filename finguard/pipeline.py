from typing import Any, Tuple, List, Dict
import asyncio
from .router import get_input_scanners, get_output_scanners

class InputPipeline:
    def __init__(self, policy: Any):
        self.policy = policy
        self.scanners = get_input_scanners(policy.risk_level, policy)

    async def run(self, req: Any) -> Tuple[bool, List[Dict[str, Any]]]:
        if not self.scanners:
            return True, []
        
        violations = []
        is_safe = True
        
        # In a real async environment, we'd run these concurrently
        # For llm_guard scanners which might be sync, we can wrap them in run_in_executor
        
        for scanner in self.scanners:
            # llm_guard scanners typically have a `scan(prompt)` method
            # returning (sanitized_prompt, is_valid, risk_score)
            _, valid, risk = scanner.scan(req.prompt)
            if not valid:
                is_safe = False
                violations.append({
                    "scanner": scanner.__class__.__name__,
                    "risk_score": risk
                })
                
        return is_safe, violations

class OutputPipeline:
    def __init__(self, policy: Any):
        self.policy = policy
        self.scanners = get_output_scanners(policy.risk_level, policy)

    async def run(self, output: str, req: Any) -> Tuple[bool, List[Dict[str, Any]]]:
        if not self.scanners:
            return True, []

        violations = []
        is_safe = True
        
        for scanner in self.scanners:
            _, valid, risk = scanner.scan(req.prompt, output)
            if not valid:
                is_safe = False
                violations.append({
                    "scanner": scanner.__class__.__name__,
                    "risk_score": risk
                })
                
        return is_safe, violations
