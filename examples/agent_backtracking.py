"""
examples/agent_backtracking.py
==============================
Demonstrates how an orchestration agent (e.g., LangChain or an internal loop)
can catch a FinGuardViolation, extract structured audit data, and recover via
LLM self-correction rather than crashing.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from finguard import FinGuard, GuardRequest
from finguard.exceptions import FinGuardViolation


async def agent_loop(task: str):
    """A simulated agent loop that tries to answer a prompt but can self-correct."""
    
    # We use a strict policy that blocks PII
    policy = {
        "policy_id": "strict_agent",
        "risk_level": "high",
        "pii": {"enabled": True}, 
        "injection": {"enabled": True},
        "audit": {"backend": "console"} # Logs to console for this demo
    }
    guard = FinGuard(policy=policy)
    
    @guard.wrap
    async def mock_llm_call(prompt: str) -> str:
        # Simulate LLM logic
        return f"Completed tool action for: {prompt[:30]}..."

    # The agent's current plan
    current_prompt = task
    attempts = 0
    max_attempts = 3
    
    print("\n🚀 Starting Agent Loop")
    print(f"Goal: {task}\n")
    
    while attempts < max_attempts:
        attempts += 1
        print(f"--- Attempt {attempts} ---")
        try:
            # 1. The agent tries to execute its plan
            response = await mock_llm_call(current_prompt)
            print(f"✅ Success: {response}")
            break
            
        except FinGuardViolation as e:
            # 2. INTROSPECTION / BACKTRACKING
            print("🚨 Blocked by FinGuard! Exception caught.")
            
            # The agent can inspect exactly WHAT failed.
            trace = e.trace
            failed_scanners = [s.scanner for s in trace.input_scanners if s.triggered]
            
            print(f"   Agent reads the trace: Failed scanners -> {failed_scanners}")
            
            if "presidio_pii" in failed_scanners:
                print("   Agent self-corrects: 'Ah, I included PII. Let me redact it and retry.'")
                # Simulated agent self-correction: rewriting prompt without the PII
                current_prompt = task.replace("1234-5678-9012-3456", "[REDACTED]")
            elif "prompt_injection" in failed_scanners:
                print("   Agent self-corrects: 'Injection detected, I should halt.'")
                break
            else:
                print("   Agent doesn't know how to fix this. Halting.")
                break


if __name__ == "__main__":
    # Task contains PII (a fake credit card number) that will trigger the Presidio scanner
    unsafe_task = "Process a refund to user account 1234-5678-9012-3456 immediately."
    
    asyncio.run(agent_loop(unsafe_task))
