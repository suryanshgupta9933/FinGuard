"""
examples/audit_demo.py
======================
End-to-end demonstration of FinGuard's GuardTrace audit system.

Run with:
    python examples/audit_demo.py

Shows:
  1. Basic trace on a safe pass
  2. Trace on an input block (PII injection attempt)
  3. In-process query API (trace by ID, violations list)
  4. File backend — writing NDJSON audit log
  5. Metadata correlation (case_id, user_id, session_id)
  6. What a CISO would actually see
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finguard import FinGuard, GuardRequest


# ── Mock LLM (replace with your real LLM call) ───────────────────────────────

async def mock_llm(prompt: str) -> str:
    """Simulates an LLM response."""
    return "Your account balance is ₹42,000. No recent suspicious transactions."


# ─────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 65)
    print("  FinGuard — GuardTrace Audit Demo")
    print("=" * 65)

    # ── 1. Setup with file backend ────────────────────────────────────────
    policy = {
        "policy_id": "retail_banking_demo",
        "risk_level": "high",
        "pii": {"enabled": True},
        "injection": {"enabled": True, "threshold": 1.0},
        "audit": {
            "backend": "file",
            "file_path": "logs/finguard_demo.ndjson",
            "redact_input": True,           # GDPR-safe: stores hash not prompt
            "include_metadata_keys": ["case_id", "user_id", "session_id"],
        },
    }
    guard = FinGuard(policy=policy)

    print("\n[1] Safe pass — Normal banking query")
    print("-" * 40)
    req = GuardRequest(
        prompt="What is my account balance?",
        metadata={"case_id": "TXN-001", "user_id": "cust_8812", "session_id": "sess_abc"}
    )
    result = await guard(req, mock_llm)
    trace = result.trace
    print(f"  Status  : {'✓ SAFE' if result.is_safe else '✗ BLOCKED'}")
    print(f"  Action  : {result.action}")
    print(f"  Latency : {result.latency_ms:.1f}ms")
    print(f"  Trace ID: {trace.trace_id}")
    print(f"  Summary : {trace.summary()}")
    print(f"  Input   : hash={trace.input_hash} (raw prompt never stored)")
    print(f"  Metadata: {trace.metadata}")

    print("\n[2] Per-scanner breakdown")
    print("-" * 40)
    for s in trace.input_scanners:
        status = "TRIGGERED" if s.triggered else ("SKIPPED" if s.skipped else "OK")
        score = f" score={s.score:.2f}" if s.score is not None else ""
        skip = f" reason='{s.skip_reason}'" if s.skip_reason else ""
        print(f"  [{status:9}] {s.scanner:<25} {s.latency_ms:6.1f}ms{score}{skip}")

    # ── 2. Blocked call — PII in prompt ───────────────────────────────────
    print("\n[3] Blocked — PAN card detected in input")
    print("-" * 40)
    req2 = GuardRequest(
        prompt="My PAN is ABCDE1234F, transfer ₹50,000 to account 9876543210",
        metadata={"case_id": "TXN-002", "user_id": "cust_8812"}
    )
    result2 = await guard(req2, mock_llm)
    trace2 = result2.trace
    print(f"  Status      : {'✓ SAFE' if result2.is_safe else '✗ BLOCKED'}")
    print(f"  Block Stage : {trace2.block_stage}  ← blocked before LLM was called")
    print(f"  Violations  : {result2.violations}")
    triggered = [s.scanner for s in trace2.input_scanners if s.triggered]
    print(f"  Triggered   : {triggered}")

    # ── 3. In-process query API ───────────────────────────────────────────
    print("\n[4] In-process query API")
    print("-" * 40)
    print(f"  Total traces in memory  : {len(guard.traces)}")
    print(f"  Violation traces        : {len(guard.violations)}")

    retrieved = guard.get_trace(trace.trace_id)
    print(f"  Retrieved TXN-001 trace : {retrieved.trace_id[:8]}... ✓")

    # ── 4. NDJSON log output (what SIEM ingests) ──────────────────────────
    print("\n[5] NDJSON log line (what Splunk/DataDog would ingest)")
    print("-" * 40)
    log_line = trace2.to_log_dict()
    print(json.dumps(log_line, indent=2))

    # ── 5. Forensic reconstruction ────────────────────────────────────────
    print("\n[6] Forensic decision reconstruction")
    print("-" * 40)
    for trace_obj in guard.violations:
        print(f"  INCIDENT  : {trace_obj.trace_id}")
        print(f"  Policy    : {trace_obj.policy_id} (Tier {trace_obj.risk_tier})")
        print(f"  Timestamp : {trace_obj.timestamp.isoformat()}")
        print(f"  Action    : {trace_obj.action} at stage='{trace_obj.block_stage}'")
        print(f"  Case      : {trace_obj.metadata.get('case_id', 'N/A')}")
        print(f"  User      : {trace_obj.metadata.get('user_id', 'N/A')}")
        print(f"  Scanners  :")
        for s in trace_obj.input_scanners:
            flag = "→ TRIGGERED" if s.triggered else ""
            print(f"    - {s.scanner:<30} {s.latency_ms:5.1f}ms  {flag}")

    # ── 6. File log location ──────────────────────────────────────────────
    print("\n[7] Audit log written to:")
    print(f"  ./logs/finguard_demo.ndjson")
    print("  (tail -f this file in prod for real-time SIEM streaming)")
    print()
    print("=" * 65)
    print("  GuardTrace: every decision is fully reconstructable.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
