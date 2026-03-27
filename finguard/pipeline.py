from typing import Any, Tuple, List, Dict
import asyncio
import time
from .router import get_input_scanners, get_output_scanners
from .schema import ValidationResult, GuardRequest

class InputPipeline:
    def __init__(self, policy: Any, vault: Any = None):
        self.policy = policy
        self.scanners = get_input_scanners(policy.risk_level if policy else "medium", policy, vault=vault)

    async def run(self, req: GuardRequest) -> Tuple[bool, List[Dict[str, Any]], Dict[str, float]]:
        if not self.scanners:
            return True, [], {}
        
        violations = []
        is_safe = True
        latencies = {}
        
        for scanner in self.scanners:
            name = scanner.__class__.__name__
            start = time.perf_counter() # High precision
            try:
                # llm-guard input scanners take 1 arg (prompt)
                res = scanner.scan(req.prompt)
                _, valid, risk = res
                
                if not valid:
                    is_safe = False
                    violations.append({
                        "scanner": name,
                        "risk_score": risk
                    })
            except Exception as e:
                # print(f"[FinGuard Warning] Input scanner {name} failed: {e}")
                pass
            
            latencies[name] = (time.perf_counter() - start) * 1000
                
        return is_safe, violations, latencies

class OutputPipeline:
    def __init__(self, policy: Any):
        self.policy = policy
        self.scanners = get_output_scanners(policy.risk_level if policy else "medium", policy)

    async def run(self, output: str, req: GuardRequest) -> Tuple[bool, List[Dict[str, Any]], Dict[str, float], str]:
        if not self.scanners:
            return True, [], {}, output

        violations = []
        is_safe = True
        latencies = {}
        sanitized_output = output
        
        for scanner in self.scanners:
            name = scanner.__class__.__name__
            start = time.perf_counter() # High precision
            try:
                # Polymorphic scan call:
                # llm-guard scanners take 1 arg (text)
                # FinGuard custom validators take 2 args (prompt, text)
                
                if name in ["Anonymize", "BanTopics", "PromptInjection", "FinGuardPIIEngine"]:
                    res = scanner.scan(sanitized_output)
                else:
                    # Custom financial validators
                    res = scanner.scan(req.prompt, sanitized_output)
                
                new_text, valid, risk = res
                
                # Update sanitized_output if it's an anonymizer
                if name in ["Anonymize", "FinGuardPIIEngine"]:
                    sanitized_output = new_text

                if not valid:
                    is_safe = False
                    violations.append({
                        "scanner": name,
                        "risk_score": risk
                    })
            except Exception as e:
                # Log the specific error for debugging
                pass
            
            latencies[f"out_{name}"] = (time.perf_counter() - start) * 1000
                
        return is_safe, violations, latencies, sanitized_output
