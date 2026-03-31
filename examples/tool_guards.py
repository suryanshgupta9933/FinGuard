"""
examples/tool_guards.py
=======================
Demonstrates how to use FinGuard's @wrap_tool decorator to protect
standard Python functions from agentic infinite loops and blocklists.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finguard import FinGuard
from finguard.exceptions import ToolCallViolation
from finguard.tools.adapters.vanilla import wrap_tool

async def main():
    print("\n" + "="*60)
    print("🛡️  FinGuard Agentic Tool Guards Demo")
    print("="*60 + "\n")

    # Initialize FinGuard with a strict tool policy
    policy = {
        "policy_id": "demo_tools",
        "risk_level": "medium",
        "tools": {
            "enabled": True,
            "blocked": ["drop_database"],
            "max_calls_per_session": 3 # Stop recursive rogue agents!
        }
    }
    guard = FinGuard(policy=policy)

    # Wrap any standard Python functions
    @wrap_tool(guard, tool_name="fetch_prices")
    async def fetch_prices(ticker: str):
        return f"Current price of {ticker} is $150.00"

    print("--- 1. Agent calls an allowed tool ---")
    try:
        res = await fetch_prices(ticker="AAPL", session_id="agent_123")
        print(f"✅ Executed perfectly: {res}\n")
    except ToolCallViolation as e:
        print(f"❌ Failed: {e}")

    print("--- 2. Agent enters a rogue infinite loop! ---")
    try:
        # It's allowed to call it 3 times max per session...
        print("Call 1...")
        await fetch_prices(ticker="AAPL", session_id="broken_agent")
        print("Call 2...")
        await fetch_prices(ticker="MSFT", session_id="broken_agent")
        print("Call 3...")
        await fetch_prices(ticker="GOOGL", session_id="broken_agent")
        
        # 4th call blows the rate limit! FinGuard saves the day.
        print("Call 4... (Should Block!)")
        await fetch_prices(ticker="AMZN", session_id="broken_agent")
    except ToolCallViolation as e:
        print(f"🚨 Blocked: {e.trace.input_scanners[0].violations[0]['reason']}\n")


if __name__ == "__main__":
    asyncio.run(main())
