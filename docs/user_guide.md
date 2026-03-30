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

## 🕵️ Observability & Auditing

As of v0.4.1, `FinGuard` ditches flat logs for structured, forensic-grade **GuardTrace** records.

### Backtracking Exceptions
If FinGuard blocks a prompt, it raises a `FinGuardViolation` containing the full trace. Your agents can catch this, inspect what triggered the block, and self-correct safely:
```python
from finguard.exceptions import FinGuardViolation

try:
    response = await banking_bot("My PAN is ABCDE1234F")
except FinGuardViolation as e:
    failed_scanners = [s.scanner for s in e.trace.input_scanners if s.triggered]
    print(f"I need to fix: {failed_scanners}") # ['presidio_pii']
```

### Full Enterprise APM
Out of the box, FinGuard supports streaming traces directly to Datadog, Splunk, Jaeger, or Langfuse metrics dashboards. 

Install the observability extras:
```bash
pip install finguard[observability]
```

Configure your policy:
```yaml
audit:
  backend: "langfuse" # Seamlessly export Span/Trace hierarchy 
  # backend: "otel"   # For native OpenTelemetry export!
```

See [Custom Policies](./custom_policies.md) for advanced configuration.
