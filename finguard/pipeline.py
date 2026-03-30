"""
finguard.pipeline
=================
Input and Output pipeline orchestrators.

Key change in v0.4: Each scanner call is wrapped by `_run_scanner()`, which:
  1. Times wall-clock latency precisely with perf_counter.
  2. Catches all exceptions and converts them to skipped ScannerTraces (never crashes).
  3. Extracts scanner name using a canonical name registry so traces have
     stable, human-readable names regardless of class name changes.
  4. Returns a ScannerTrace per invocation — the pipeline returns the full list
     alongside the existing violations/latencies dicts for backwards compatibility.
"""
from typing import Any, Tuple, List, Dict, Optional
import asyncio
import time

from .router import get_input_scanners, get_output_scanners
from .schema import ValidationResult, GuardRequest
from .audit.trace import ScannerTrace

# ── Canonical scanner name registry ─────────────────────────────────────────
# Maps class name → stable audit log name. Decoupled from class hierarchy.
_SCANNER_NAMES: Dict[str, str] = {
    "PromptInjectionWrapper": "prompt_injection",
    "PromptInjection": "prompt_injection",
    "BanTopics": "topic_boundary",
    "FinGuardPIIEngine": "presidio_pii",
    "IndianFinancialPII": "regex_pii_fast",
    "PMLAScanner": "pmla_detection",
    "Anonymize": "llm_guard_anonymize",
    "NumericalClaimValidator": "numerical_validator",
    "CompliancePhraseDetector": "compliance_phrases",
}


def _canonical_name(scanner: Any) -> str:
    cls = scanner.__class__.__name__
    return _SCANNER_NAMES.get(cls, cls.lower())


# ── Core scanner runner ──────────────────────────────────────────────────────

def _run_scanner(scanner: Any, stage: str, *args) -> Tuple[Optional[tuple], ScannerTrace]:
    """
    Execute a single scanner, capture its output and emit a ScannerTrace.
    
    Returns (raw_result, ScannerTrace).
    raw_result is None if the scanner errored or was skipped.
    """
    name = _canonical_name(scanner)
    t0 = time.perf_counter()
    
    try:
        raw = scanner.scan(*args)
        latency = (time.perf_counter() - t0) * 1000
        
        # All scanners return (text, is_valid, risk_score)
        _, valid, score = raw
        
        strace = ScannerTrace(
            scanner=name,
            stage=stage,
            triggered=not valid,
            score=round(float(score), 4),
            latency_ms=round(latency, 2),
        )
        return raw, strace
        
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        strace = ScannerTrace(
            scanner=name,
            stage=stage,
            triggered=False,
            latency_ms=round(latency, 2),
            skipped=True,
            skip_reason=f"{type(e).__name__}: {str(e)[:120]}",
        )
        return None, strace


# ── Input Pipeline ───────────────────────────────────────────────────────────

class InputPipeline:
    def __init__(self, policy: Any, vault: Any = None):
        self.policy = policy
        self.scanners = get_input_scanners(
            policy.risk_level if policy else "medium", policy, vault=vault
        )

    async def run(
        self, req: GuardRequest
    ) -> Tuple[bool, List[Dict], Dict[str, float], List[ScannerTrace]]:
        """
        Returns (is_safe, violations, latencies, scanner_traces).
        
        scanner_traces is the new addition — ordered list of ScannerTrace objects
        for inclusion in GuardTrace.
        """
        if not self.scanners:
            return True, [], {}, []

        violations = []
        is_safe = True
        latencies = {}
        scanner_traces: List[ScannerTrace] = []

        for scanner in self.scanners:
            cls_name = scanner.__class__.__name__
            raw, strace = _run_scanner(scanner, "input", req.prompt)
            scanner_traces.append(strace)
            latencies[strace.scanner] = strace.latency_ms

            if raw is not None:
                _, valid, risk = raw
                if not valid:
                    is_safe = False
                    strace.violations.append({
                        "scanner": strace.scanner,
                        "risk_score": risk
                    })
                    violations.append({
                        "scanner": strace.scanner,
                        "risk_score": risk
                    })

        return is_safe, violations, latencies, scanner_traces


# ── Output Pipeline ──────────────────────────────────────────────────────────

# Scanners that return sanitized text as first element (anonymizers/redactors)
_REDACTING_SCANNERS = {"presidio_pii", "llm_guard_anonymize"}
# Scanners that take (prompt, output) instead of just (output)
_TWO_ARG_SCANNERS = {"numerical_validator", "compliance_phrases", "pmla_detection"}


class OutputPipeline:
    def __init__(self, policy: Any):
        self.policy = policy
        self.scanners = get_output_scanners(
            policy.risk_level if policy else "medium", policy
        )

    async def run(
        self, output: str, req: GuardRequest
    ) -> Tuple[bool, List[Dict], Dict[str, float], str, List[ScannerTrace]]:
        """
        Returns (is_safe, violations, latencies, sanitized_output, scanner_traces).
        """
        if not self.scanners:
            return True, [], {}, output, []

        violations = []
        is_safe = True
        latencies = {}
        sanitized = output
        scanner_traces: List[ScannerTrace] = []

        for scanner in self.scanners:
            name = _canonical_name(scanner)
            
            # Choose correct call signature
            if name in _TWO_ARG_SCANNERS:
                raw, strace = _run_scanner(scanner, "output", req.prompt, sanitized)
            else:
                raw, strace = _run_scanner(scanner, "output", sanitized)

            scanner_traces.append(strace)
            latencies[f"out_{strace.scanner}"] = strace.latency_ms

            if raw is not None:
                new_text, valid, risk = raw

                # Persist redacted output from anonymizers
                if name in _REDACTING_SCANNERS:
                    sanitized = new_text

                if not valid:
                    is_safe = False
                    strace.violations.append({
                        "scanner": strace.scanner,
                        "risk_score": risk
                    })
                    violations.append({
                        "scanner": strace.scanner,
                        "risk_score": risk
                    })

        return is_safe, violations, latencies, sanitized, scanner_traces
