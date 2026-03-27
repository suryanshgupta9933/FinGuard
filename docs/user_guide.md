# FinGuard User Guide

FinGuard is a modular safety orchestration layer for financial LLM applications. It wraps any async LLM function with a tiered pipeline covering PII, injection, and compliance.

## Quick Start

```bash
pip install finguard
```

```python
import asyncio
from finguard import FinGuard

guard = FinGuard(policy="retail_banking")

@guard.wrap
async def banking_bot(prompt: str) -> str:
    return await llm.generate(prompt)

asyncio.run(banking_bot("My PAN is ABCDE1234F, help me file taxes"))
# → BLOCKED: Detected IN_PAN in prompt
```

## Built-In Policies

| Policy | Best For | Latency |
| :--- | :--- | :--- |
| `default` | General financial bot | ~55ms |
| `fast_lane` | IVR, SMS, high-throughput | ~35ms |
| `retail_banking` | Branch chatbots, net banking | ~55ms |
| `wealth_advisor` | Robo-advisors (SEBI compliance) | ~180ms |
| `high_security` | Fraud ops, compliance officers | ~180ms |

## Pipeline Architecture

```
Prompt → [Input Pipeline] → LLM → [Output Pipeline] → Response
```

**Input Pipeline** (runs before the LLM):
- PII detection and blocking (Presidio NER or Regex fast-path)
- PMLA high-value transfer detection
- Prompt injection classification (ONNX AI)
- Topic boundary enforcement

**Output Pipeline** (runs after the LLM):
- PII redaction in responses (if `redact_output: true`)
- Numerical hallucination check
- Compliance phrase enforcement (SEBI/RBI disclaimers)

## Observability

Every `GuardResult` exposes `component_latencies`:

```python
res = await guard(req, llm_fn)
print(res.component_latencies)
# {'FinGuardPIIEngine': 15.4ms, 'PromptInjection': 37.2ms, 'BanTopics': 96.1ms}
```

See [Custom Policies](./custom_policies.md) for advanced configuration.
