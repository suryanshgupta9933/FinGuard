# FinGuard User Guide

Welcome to FinGuard! FinGuard is designed to be the security perimeter for your financial LLM applications.

## Getting Started

1. **Install FinGuard:**
   ```bash
   pip install finguard
   ```

2. **Basic Usage:**
   You can secure any async LLM callable by importing `FinGuard` and wrapping it with a policy string.
   
   ```python
   import asyncio
   from finguard import FinGuard

   guard = FinGuard(policy="banking_support_chatbot_v1")

   @guard.wrap
   async def my_llm_call(prompt: str) -> str:
       # Call your LLM here (OpenAI, Anthropic, or Local)
       return "Processed: " + prompt

   asyncio.run(my_llm_call("Can you show my account balance?"))
   ```

3. **Built-In Policies:**
   - `banking_support_chatbot_v1`: Disables numerical checks, fast risk routing, PII anonymization.
   - `wealth_mgmt_assistant_v1`: Full strict compliance checks, checking guaranteed returns, hallucinated numbers.
   - `fraud_ops_agent_v1`: PII retention and tracking.

## Pipeline Architecture
FinGuard intercepts requests twice:
1. **Input Pipeline:** Runs before the LLM. It intercepts prompt injection and banned topics.
2. **Output Pipeline:** Runs after the LLM. It intercepts unapproved financial advice and ungrounded numeric claims.

Violations are logged automatically to `AuditLogger`.

For advanced usage, see [Custom Policies](./custom_policies.md).
