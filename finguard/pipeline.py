from typing import Any, Tuple, List, Dict
import asyncio
from .router import get_input_scanners, get_output_scanners
from .schema import ValidationResult, GuardRequest

class InputPipeline:
    def __init__(self, policy: Any):
        self.policy = policy
        self.scanners = get_input_scanners(policy.risk_level if policy else "medium", policy)

    async def run(self, req: GuardRequest) -> Tuple[bool, List[Dict[str, Any]]]:
        if not self.scanners:
            return True, []
        
        violations = []
        is_safe = True
        
        for scanner in self.scanners:
            try:
                _, valid, risk = scanner.scan(req.prompt)
                if not valid:
                    is_safe = False
                    violations.append({
                        "scanner": scanner.__class__.__name__,
                        "risk_score": risk
                    })
            except Exception as e:
                print(f"[FinGuard Warning] Scanner {scanner.__class__.__name__} failed: {e}")
                
        return is_safe, violations

class OutputPipeline:
    def __init__(self, policy: Any):
        self.policy = policy
        self.scanners = get_output_scanners(policy.risk_level if policy else "medium", policy)

    async def run(self, output: str, req: GuardRequest) -> Tuple[bool, List[Dict[str, Any]]]:
        if not self.scanners:
            return True, []

        violations = []
        is_safe = True
        
        for scanner in self.scanners:
            try:
                _, valid, risk = scanner.scan(req.prompt, output)
                if not valid:
                    is_safe = False
                    violations.append({
                        "scanner": scanner.__class__.__name__,
                        "risk_score": risk
                    })
            except Exception as e:
                print(f"[FinGuard Warning] Output scanner {scanner.__class__.__name__} failed: {e}")
                
        return is_safe, violations
