from typing import Any, Dict, List, Optional
import json

class AuditLogger:
    def __init__(self, config=None):
        self.config = config
        self.backend = config.backend if config else "json"
        
    def record(self, req: Any, action: str, violations: List[Dict[str, Any]], output: Optional[str] = None, latency_ms: float = 0.0) -> Any:
        from .core import GuardResult
        
        # Create standard result
        is_safe = (action == "pass")
        result = GuardResult(
            output=output,
            is_safe=is_safe,
            violations=violations,
            action=action,
            latency_ms=latency_ms
        )
        
        # Log logic
        log_entry = {
            "prompt": req.prompt,
            "metadata": req.metadata,
            "action": action,
            "is_safe": is_safe,
            "violations": violations,
            "latency_ms": latency_ms
        }
        
        if self.backend == "json":
            # For this MVP, we just print or could append to a stream
            print(f"[FinGuard JSON Audit] {json.dumps(log_entry)}")
            
        return result
