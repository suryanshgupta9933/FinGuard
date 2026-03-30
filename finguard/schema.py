from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .audit.trace import GuardTrace

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
    trace: Optional["GuardTrace"] = None
    """Full forensic trace of this guard invocation. None if tracing is disabled."""
