import time
from typing import Dict

class SessionTracker:
    """
    Prevents Agent Infinite Loops by tracking total tool calls per session.
    A basic in-memory LRU tracker that enforces `max_calls_per_session`.
    """
    
    def __init__(self, max_calls: int = 50, ttl_seconds: int = 3600):
        self.max_calls = max_calls
        self.ttl_seconds = ttl_seconds
        # dict: session_id -> {"count": 0, "last_updated": time.time()}
        self._counts: Dict[str, Dict] = {}

    def is_allowed(self, session_id: str) -> bool:
        """Checks if a session has exceeded its maximum tool call limit."""
        if not session_id or self.max_calls <= 0:
            return True
            
        now = time.time()
        
        # Cleanup expired sessions lazily
        expired = [sid for sid, data in self._counts.items() 
                   if now - data["last_updated"] > self.ttl_seconds]
        for sid in expired:
            del self._counts[sid]

        session_data = self._counts.get(session_id, {"count": 0, "last_updated": now})
        
        return session_data["count"] < self.max_calls
        
    def increment(self, session_id: str) -> None:
        """Increments the tracked tool calls for a given session."""
        if not session_id:
            return
            
        now = time.time()
        if session_id not in self._counts:
            self._counts[session_id] = {"count": 1, "last_updated": now}
        else:
            self._counts[session_id]["count"] += 1
            self._counts[session_id]["last_updated"] = now
            
    def get_count(self, session_id: str) -> int:
        if session_id not in self._counts:
            return 0
        return self._counts[session_id]["count"]
