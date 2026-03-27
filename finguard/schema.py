from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ValidationResult:
    action: str = "pass"
    is_safe: bool = True
    violations: List[Dict[str, Any]] = field(default_factory=list)
    risk_score: float = 0.0

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
    component_latencies: Dict[str, float] = field(default_factory=dict)
