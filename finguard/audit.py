from typing import Any, Dict, List, Optional
import json

class AuditLogger:
    def __init__(self, config=None):
        self.config = config
        self.backend = config.backend if config else "json"
        
    def record(self, req: Any, action: str, violations: List[Dict[str, Any]], 
               output: Optional[str] = None, latency_ms: float = 0.0, 
               component_latencies: Dict[str, float] = None) -> Any:
        from .schema import GuardResult
        
        # Create standard result
        is_safe = (action == "pass")
        result = GuardResult(
            output=output,
            is_safe=is_safe,
            violations=violations,
            action=action,
            latency_ms=latency_ms,
            component_latencies=component_latencies or {}
        )
        
        # Log logic
        log_entry = {
            "prompt": req.prompt,
            "metadata": req.metadata,
            "action": action,
            "is_safe": is_safe,
            "violations": violations,
            "latency_ms": latency_ms,
            "component_latencies": component_latencies or {}
        }
        
        if self.backend == "json":
            # Silent by default, but we can print a summary for the developer
            print(f"\n[FinGuard Audit] {action.upper()} | Prompt: {req.prompt[:50]}...")
            if component_latencies:
                lats = ", ".join([f"{k}: {v:.1f}ms" for k, v in component_latencies.items()])
                print(f"       Latency: {latency_ms:.1f}ms total | {lats}")
            
        return result
