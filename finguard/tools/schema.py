from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ToolCallRequest(BaseModel):
    """Represents a tool call attempt intercepted by the framework."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class ToolCallResult(BaseModel):
    """Result of a Tool Call Guard evaluation."""
    tool_name: str
    is_safe: bool
    action: str  # "pass" | "block" | "hitl" (human-in-the-loop)
    block_reason: Optional[str] = None
    risk_tier: int = 1
    latency_ms: float = 0.0
