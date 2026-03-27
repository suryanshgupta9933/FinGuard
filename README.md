# FinGuard

> **An open-source, production-ready LLM safety orchestration layer built specifically for financial AI.**

[![PyPI version](https://img.shields.io/pypi/v/finguard.svg)](https://pypi.org/project/finguard/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why FinGuard?

Generic guardrail tools (like pure NeMo or LlamaGuard) are trained on general internet hazards—toxicity, violence, jailbreaks. However, financial chatbots and agents fail because of **domain-specific risks**: missing required disclaimers, hallucinating numerical returns, and confidently giving non-compliant investment advice. 

FinGuard provides the critical "orchestration glue"—a robust 20% layer that wraps enterprise-grade open-source scanners (`llm-guard`, `presidio`) with **financial-specific validators** out-of-the-box.

### The FinGuard Difference:
1. **Indian-Specific PII Native Support**: Generic tools struggle with PAN, Aadhaar, and Demat accounts. FinGuard injects custom entity recognizers directly into its Presidio engine.
2. **Numerical Hallucination Control**: Native validators to cross-check numbers from the context window against LLM output to prevent confidently hallucinated percentages.
3. **Compliance Phrase Detection**: Instantly flags SEBI/RBI violating phrases (e.g. `"risk-free"`, `"guaranteed returns"`) and asserts required disclaimers.
4. **Risk-based Routing**: Allows keeping low-risk inputs blazing fast (~15-50ms) using heuristic scanners, while silently routing high-risk prompts to heavier local LLMs.

## Installation

```bash
pip install finguard
```

## Quick Start (Plug-and-Play)

FinGuard is entirely driven by declarative YAML policies. No spaghetti code. 

**Ship with confidence using our 3 built-in profiles out of the box:**
- `banking_support_chatbot_v1` : Designed for low-latency support bots. Disables LLM judge, enables PII anonymization. (<60ms)
- `wealth_mgmt_assistant_v1` : Full stack, strict SEBI compliance, rigorous prompt injection & hallucination boundaries. 1-year audit retention.
- `fraud_ops_agent_v1` : Agentic setup, PII round-trip anonymization, 7-year PMLA audit retention.

### 1. Wrap your LLM using a Built-in Policy
```python
import asyncio
from finguard import FinGuard

# 1. Initialize guard with a built-in policy name (or path to a custom YAML)
guard = FinGuard(policy="wealth_mgmt_assistant_v1")

# 2. Add the wrapper decorator to your async LLM call
@guard.wrap
async def chatbot_reply(prompt: str) -> str:
    # Your internal OpenAI/Anthropic/Local LLM call
    return await my_llm_client.chat(prompt)

# 3. Use it! Everything is scanned asynchronously.
async def main():
    try:
        response = await chatbot_reply("What mutual fund guarantees 20% returns?")
        print(response)
    except Exception as e:
        print(f"FinGuard Intercepted: {e}")

asyncio.run(main())
```

## Core Architecture

FinGuard uses asynchronous pipelines (`InputPipeline` & `OutputPipeline`) to process parallel checks.

| Name | Type | Underlying Engine | Latency (Avg) |
|---|---|---|---|
| **Prompt Injection** | Input | `llm-guard` | ~40ms |
| **Ban Topics** | Input | `llm-guard` (Zero-Shot) | ~80ms |
| **Custom Indian PII** | Input/Output | `presidio` custom registries | ~15ms |
| **Compliance Phrases** | Output | FinGuard Native (Regex + Disclaimers) | ~5ms |
| **Numerical Claims** | Output | FinGuard Native | ~5ms |

## Performance & Benchmarks

*Note: The latency targets in the architecture table are optimistic, assuming mid-to-high tier hardware (e.g. NVIDIA GPUs or Apple M-series chips). Running heavy NLP packages (like `llm-guard`) purely on CPU will add significant overhead.*

To measure the Ground Truth performance on your target deployment, run the native benchmark script:
```bash
python benchmark.py
```

## Live Demos

Test the actual pipelines safely in your browser:
* [📖 Try the Google Colab Notebook Demo](notebooks/FinGuard_Demo.ipynb) 

## Documentation

- [📘 General User Guide](docs/user_guide.md)
- [⚙️ Creating Custom YAML Policies](docs/custom_policies.md)

## Building the Package (PyPI)

If you are a maintainer looking to build and push this package to PyPI:
```bash
uv build
twine upload dist/*
```

## Roadmap (v1 and beyond)
- [x] Initial Open Source Release (v0.1)
- [ ] Connect Numerical Claim Validation to localized fastText contextual verifiers.
- [ ] Add natively supported `NeMo Guardrails` fallback generation mode.
- [ ] Incorporate comprehensive OpenTelemetry trace dashboards.

---
*Built openly for the financial AI community.*
