"""
finguard.audit.backends.base
============================
Abstract base class for all audit backends.

Design decision — Backend interface is intentionally minimal:
  emit(trace) is the only required method.
  flush() is optional for batched/async backends.
This makes it trivial for enterprise users to implement a custom backend
(Splunk, DataDog, BigQuery, etc.) in ~10 lines.
"""
from abc import ABC, abstractmethod
from ..trace import GuardTrace


class AuditBackend(ABC):
    """Base class for pluggable audit backends."""

    @abstractmethod
    def emit(self, trace: GuardTrace) -> None:
        """
        Persist or forward a single GuardTrace.
        Must be synchronous and non-blocking for the hot path.
        """

    def flush(self) -> None:
        """Optional: flush buffered traces. Called on shutdown."""
