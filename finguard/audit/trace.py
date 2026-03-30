"""
finguard.audit.trace
====================
Core forensic data models for FinGuard's immutable audit trail.

Design decisions:
- Uses Pydantic for full JSON serialization, schema export, and validation.
- input_hash stores SHA-256[:16] fingerprint — raw prompts are NEVER persisted
  by default. This is GDPR/data-residency safe for financial prod environments.
- trace_id is a UUID4 — globally unique, can be referenced in external SIEMs.
- ScannerTrace.skipped allows incident response to distinguish "scanner didn't
  fire" from "scanner was bypassed or timed out" — a critical forensic distinction
  that most tools miss.
"""
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import hashlib


class ScannerTrace(BaseModel):
    """Per-scanner execution record within a single guard invocation."""
    
    scanner: str
    """Canonical scanner name e.g. 'presidio_pii', 'prompt_injection', 'numerical_validator'"""
    
    stage: str
    """'input' or 'output' — which pipeline stage this scanner ran in."""
    
    triggered: bool
    """True if scanner detected a violation and contributed to a block/flag."""
    
    score: Optional[float] = None
    """Confidence/risk score (0.0–1.0) if the scanner provides one."""
    
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    """Structured violation detail — entity type, location, severity, etc."""
    
    latency_ms: float
    """Wall-clock time this scanner consumed in milliseconds."""
    
    skipped: bool = False
    """True if scanner was bypassed (timeout, error, or explicitly disabled)."""
    
    skip_reason: Optional[str] = None
    """Human-readable reason for skip — e.g. 'timeout', 'policy_disabled', 'error'."""


class GuardTrace(BaseModel):
    """
    Immutable forensic record of a single FinGuard invocation.
    
    This is the 'digital ledger entry' — every guard decision produces exactly
    one GuardTrace, capturing the full decision path from input through output
    scanners to the final action taken.
    
    Storage: append-only. Traces should never be mutated after creation.
    """
    
    # ── Identity ──────────────────────────────────────────────────────────
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """Globally unique trace identifier. Use this to correlate across systems."""
    
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    """UTC timestamp of when the guard invocation began."""
    
    # ── Policy context ────────────────────────────────────────────────────
    policy_id: str
    """The policy that governed this invocation e.g. 'retail_banking'."""
    
    policy_version: str = "0.0"
    """Semantic version of the policy config, if set."""
    
    risk_tier: int = 1
    """Risk classification: 1 (low) | 2 (medium) | 3 (high)."""
    
    # ── Input fingerprint (privacy-safe) ─────────────────────────────────
    input_hash: str
    """SHA-256 fingerprint of the input prompt (first 16 hex chars).
    Never the raw prompt — safe for GDPR/data-residency environments."""
    
    input_length: int
    """Character length of the input prompt."""
    
    # ── Scanner breakdown ─────────────────────────────────────────────────
    input_scanners: List[ScannerTrace] = Field(default_factory=list)
    """Ordered list of input scanner traces, in execution order."""
    
    output_scanners: List[ScannerTrace] = Field(default_factory=list)
    """Ordered list of output scanner traces, in execution order."""
    
    # ── Decision ──────────────────────────────────────────────────────────
    is_safe: bool
    """Final safety verdict."""
    
    action: str
    """Terminal action: 'pass' | 'block' | 'reask' | 'fix'."""
    
    block_stage: Optional[str] = None
    """'input' if blocked before LLM call, 'output' if blocked after. None if passed."""
    
    total_latency_ms: float
    """End-to-end wall-clock time in milliseconds."""
    
    # ── Caller metadata (opt-in) ──────────────────────────────────────────
    metadata: Dict[str, Any] = Field(default_factory=dict)
    """Arbitrary caller-injected context: case_id, user_id, session_id, agent_id.
    Use PolicyConfig.audit.include_metadata_keys to control what is persisted."""
    
    # ── Methods ───────────────────────────────────────────────────────────
    @classmethod
    def fingerprint(cls, text: str) -> str:
        """Returns a short SHA-256 fingerprint. Not reversible — safe for logs."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    
    def to_log_dict(self) -> Dict[str, Any]:
        """Returns a flat dict optimised for NDJSON/SIEM ingestion."""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "policy_id": self.policy_id,
            "risk_tier": self.risk_tier,
            "input_hash": self.input_hash,
            "input_length": self.input_length,
            "input_scanner_count": len(self.input_scanners),
            "output_scanner_count": len(self.output_scanners),
            "triggered_scanners": [
                s.scanner for s in self.input_scanners + self.output_scanners
                if s.triggered
            ],
            "skipped_scanners": [
                {"scanner": s.scanner, "reason": s.skip_reason}
                for s in self.input_scanners + self.output_scanners
                if s.skipped
            ],
            "is_safe": self.is_safe,
            "action": self.action,
            "block_stage": self.block_stage,
            "total_latency_ms": round(self.total_latency_ms, 2),
            **{f"meta_{k}": v for k, v in self.metadata.items()},
        }
    
    def summary(self) -> str:
        """Human-readable one-liner for developer logs and CLI output."""
        status = "✓ PASS" if self.is_safe else "✗ BLOCK"
        triggered = [
            s.scanner for s in self.input_scanners + self.output_scanners
            if s.triggered
        ]
        triggered_str = f" | triggered: {', '.join(triggered)}" if triggered else ""
        return (
            f"[{status}] {self.policy_id} | "
            f"{self.total_latency_ms:.1f}ms | "
            f"trace:{self.trace_id[:8]}{triggered_str}"
        )
