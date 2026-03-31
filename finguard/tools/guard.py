import time
import logging
from typing import Optional

from finguard.config import ToolConfig
from finguard.tools.schema import ToolCallRequest, ToolCallResult
from finguard.tools.tracker import SessionTracker

logger = logging.getLogger("finguard.tools")

class ToolCallGuard:
    """
    Evaluates requested tool executions against a declarative `ToolConfig`.
    Enforces allowlists, blocklists, and session rate limits.
    """
    def __init__(self, config: Optional[ToolConfig] = None):
        self.config = config or ToolConfig()
        self.tracker = SessionTracker(max_calls=self.config.max_calls_per_session)

    def evaluate(self, request: ToolCallRequest) -> ToolCallResult:
        start_time = time.perf_counter()
        
        # Fast path if disabled
        if not self.config.enabled:
            latency = (time.perf_counter() - start_time) * 1000
            return ToolCallResult(tool_name=request.tool_name, is_safe=True, action="pass", latency_ms=latency)
            
        tool_name = request.tool_name
        
        # 1. Rate Limiting Check
        if request.session_id:
            if not self.tracker.is_allowed(request.session_id):
                latency = (time.perf_counter() - start_time) * 1000
                logger.warning(f"Session {request.session_id} exceeded max tool calls.")
                return ToolCallResult(
                    tool_name=tool_name,
                    is_safe=False,
                    action="block",
                    block_reason=f"Exceeded max_calls_per_session ({self.config.max_calls_per_session})",
                    risk_tier=2,
                    latency_ms=latency
                )

        # 2. Blocklist Check
        if tool_name in self.config.blocked:
            latency = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Blocked explicitly disallowed tool: {tool_name}")
            return ToolCallResult(
                tool_name=tool_name,
                is_safe=False,
                action="block",
                block_reason=f"Tool '{tool_name}' is explicitly explicitly blocked.",
                risk_tier=3,
                latency_ms=latency
            )
            
        # 3. Allowlist Check (Strict mode if allowed list is populated)
        if self.config.allowed and tool_name not in self.config.allowed:
            latency = (time.perf_counter() - start_time) * 1000
            logger.warning(f"Blocked tool not in allowlist: {tool_name}")
            return ToolCallResult(
                tool_name=tool_name,
                is_safe=False,
                action="block",
                block_reason=f"Tool '{tool_name}' is not in the allowed list.",
                risk_tier=2,
                latency_ms=latency
            )

        # 4. Success -> Increment Tracker
        if request.session_id:
            self.tracker.increment(request.session_id)

        latency = (time.perf_counter() - start_time) * 1000
        return ToolCallResult(
            tool_name=tool_name, 
            is_safe=True, 
            action="pass",
            latency_ms=latency
        )
