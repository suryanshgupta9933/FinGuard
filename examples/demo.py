import asyncio
import os
import sys

# Ensure finguard is in path for demo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from finguard import FinGuard

# Load the guard with a built-in YAML policy
guard = FinGuard(policy="wealth_mgmt_assistant_v1")

@guard.wrap
async def dummy_financial_llm(prompt: str) -> str:
    """Mock LLM function that produces a predetermined response based on the prompt scenario."""
    
    if "crypto" in prompt.lower():
        # Scenario 1: Will be blocked on INPUT (BanTopics) because crypto_trading is banned
        return "You should invest in crypto coins."
        
    elif "guaranteed" in prompt.lower():
        # Scenario 2: Allowed prompt but the response violates compliance (guaranteed returns)
        return "Based on your portfolio, I can guarantee returns of 20% next year! This is risk-free."
        
    else:
        # Scenario 3: Clean prompt and clean response
        return "Here is your transaction history for October. No issues found. This is not personalized investment advice."

async def run_scenario(name: str, prompt: str):
    print(f"\n--- Scenario: {name} ---")
    print(f"User Prompt: {prompt}")
    
    try:
        response = await dummy_financial_llm(prompt)
        print(f"Final LLM Response:\n{response}")
    except Exception as e:
        print(f"\n[BLOCKED] Request was intercepted by FinGuard:\n{str(e)}")


async def main():
    print("Initializing FinGuard Scenarios...\n")
    
    # Scenario 1: Trigger Input Guard (Ban Topics)
    await run_scenario(
        "Off-Topic Input", 
        "What is the expected return on my crypto trading?"
    )
    
    # Scenario 2: Trigger Output Guard (Compliance Violations / Hallucinated Numbers)
    await run_scenario(
        "Compliance Violation (Output Guard)", 
        "Is my portfolio performing well? Give me a guaranteed forecast."
    )
    
    # Scenario 3: Safe execution
    await run_scenario(
        "Valid Request", 
        "Can you show me my recent transaction history?"
    )

if __name__ == "__main__":
    asyncio.run(main())
