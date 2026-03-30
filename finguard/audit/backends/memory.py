"""
finguard.audit.backends.memory
==============================
In-memory circular buffer backend — default for dev/test environments.

Design decision — circular deque with configurable maxlen:
  - Zero I/O overhead on the hot path (just a list append).
  - Acts as an in-process query store; useful for test assertions
    and short-lived dashboards.
  - In prod, swap this for file or langfuse backend.
  - Thread-safe: deque append/popleft are atomic in CPython.
"""
from collections import deque
from typing import List, Optional
from .base import AuditBackend
from ..trace import GuardTrace


class MemoryBackend(AuditBackend):
    """Keeps the last N traces in memory. Default backend."""

    def __init__(self, maxlen: int = 1000):
        self._buffer: deque[GuardTrace] = deque(maxlen=maxlen)

    def emit(self, trace: GuardTrace) -> None:
        self._buffer.append(trace)

    def get_all(self) -> List[GuardTrace]:
        """Return all buffered traces, oldest first."""
        return list(self._buffer)

    def get_by_id(self, trace_id: str) -> Optional[GuardTrace]:
        for t in self._buffer:
            if t.trace_id == trace_id:
                return t
        return None

    def get_by_policy(self, policy_id: str) -> List[GuardTrace]:
        return [t for t in self._buffer if t.policy_id == policy_id]

    def get_violations(self) -> List[GuardTrace]:
        """Return only traces where a block or violation occurred."""
        return [t for t in self._buffer if not t.is_safe]

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
