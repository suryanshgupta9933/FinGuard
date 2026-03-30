"""
finguard.audit.backends.file
=============================
Append-only NDJSON file backend — production-safe, SIEM-compatible.

Design decisions:
- NDJSON (newline-delimited JSON): one trace per line, no wrapping array.
  This is the format expected by Splunk, DataDog, Elastic, and most SIEMs.
  Streaming-compatible — can be tailed with `tail -f` in real time.

- Append-only + rotation: file is opened in 'a' mode and never overwritten.
  This is intentional for forensic integrity — historical traces are never
  at risk of corruption from a new write cycle.

- to_log_dict() flattens the trace: nested scanner lists become flat fields
  like 'triggered_scanners' and 'skipped_scanners'. This keeps log lines
  single-depth and grep/awk-friendly.

- File path supports strftime patterns: e.g. "logs/finguard_%Y-%m-%d.ndjson"
  for automatic daily rotation without a log rotation daemon.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from .base import AuditBackend
from ..trace import GuardTrace


class FileBackend(AuditBackend):
    """
    Appends one JSON line per GuardTrace to a log file.
    
    Usage:
        backend = FileBackend("logs/finguard.ndjson")
        # Or with daily rotation:
        backend = FileBackend("logs/finguard_%Y-%m-%d.ndjson")
    """

    def __init__(self, path: str):
        self._path_template = path

    def _resolve_path(self) -> Path:
        """Resolves strftime patterns in the path for rotation support."""
        resolved = datetime.now(timezone.utc).strftime(self._path_template)
        p = Path(resolved)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def emit(self, trace: GuardTrace) -> None:
        path = self._resolve_path()
        line = json.dumps(trace.to_log_dict(), ensure_ascii=False)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
