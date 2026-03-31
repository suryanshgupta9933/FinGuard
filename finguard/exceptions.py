"""
finguard.exceptions
===================
Custom exceptions for FinGuard to enable robust error handling and
agentic backtracking/self-correction.
"""

from typing import Optional
from .audit.trace import GuardTrace

class FinGuardException(Exception):
    """Base exception for all FinGuard errors."""
    pass

class FinGuardViolation(FinGuardException):
    """
    Raised when a prompt or document is blocked by a safety policy.
    
    Agents can catch this exception to inspect the `trace` attribute
    and dynamically backtrack or self-correct based on exactly which
    scanners failed.
    """
    def __init__(self, message: str, trace: Optional[GuardTrace] = None):
        super().__init__(message)
        self.trace = trace

class ToolCallViolation(FinGuardViolation):
    """
    Raised when an agent attempts to execute a tool that violates the active policy
    (e.g., executing a blocked tool or exceeding the max_calls_per_session).
    """
    pass
