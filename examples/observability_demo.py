"""
examples/observability_demo.py
==============================

This script demonstrates FinGuard's OpenTelemetry and Langfuse integration
live. Since we don't have a DataDog or Jaeger collector running locally,
we'll wire the OpenTelemetry SDK to print spans directly to the console so
you can see the exact telemetry being exported.

Usage:
    uv run examples/observability_demo.py
"""
import asyncio
import sys
import os

# Add root to python path to import finguard normally
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Ensure OTEL is configured to dump to console before we start ────────
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter

# Setup Trace Provider and Console Exporter
provider = TracerProvider()
processor = SimpleSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
# ────────────────────────────────────────────────────────────────────────

from finguard import FinGuard
from finguard.exceptions import FinGuardViolation


async def main():
    print("\n" + "="*60)
    print("🛡️  FinGuard Enterprise Observability Demo")
    print("="*60 + "\n")

    # Initialize FinGuard with observability backends
    policy = {
        "policy_id": "demo_policy",
        "risk_level": "medium",
        "pii": {"enabled": True}, 
        "injection": {"enabled": True},
        # You can specify a list or string. The console exporter above will output OTEL data.
        # It will also attempt to use Langfuse if you have LANGFUSE_PUBLIC_KEY in env
        "audit": {
            "backend": "otel",
            "include_metadata_keys": ["session_id", "user_id"]
        }
    }
    
    guard = FinGuard(policy=policy)
    
    @guard.wrap
    async def process_transaction(prompt: str, **kwargs) -> str:
        return f"Simulation success: {prompt[:20]}..."

    print("--- 1. Processing a Clean Request ---")
    try:
        req = "Transfer $500 to my checking account."
        # Notice we are passing session_id and user_id for visual grouping!
        res = await process_transaction(req, session_id="app_123", user_id="user_22")
        print(f"✅ Allowed: {res}\n")
    except FinGuardViolation as e:
        print(f"❌ Blocked: {e}")

    print("--- 2. Processing a Financial PII Violation ---")
    try:
        bad_req = "Here is my credit card: 4532-1234-5678-9012"
        await process_transaction(bad_req, session_id="app_123", user_id="user_22")
    except FinGuardViolation as e:
        failed_scanners = [s.scanner for s in e.trace.input_scanners if s.triggered]
        print(f"🚨 Blocked: Found PII {failed_scanners}")
    
    # Let the console exporter flush
    await asyncio.sleep(0.5)
    print("\n✅ Demo Complete! You should see the OpenTelemetry spans printed above.")

if __name__ == "__main__":
    asyncio.run(main())
