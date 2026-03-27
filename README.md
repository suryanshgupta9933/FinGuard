# FinGuard

> **An open-source, production-ready LLM safety orchestration layer built specifically for financial AI.**

[![PyPI version](https://img.shields.io/pypi/v/finguard.svg)](https://pypi.org/project/finguard/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Why FinGuard?

Generic guardrail tools fail in finance because of **domain-specific risks**: missing disclaimers, hallucinating returns, and non-compliant advice. 

FinGuard provides the critical "orchestration glue"—wrapping enterprise-grade scanners (`llm-guard`, `presidio`) with **financial-specific validators** out-of-the-box.

### The FinGuard Difference:
1. **Indian-Specific PII Native Support**: PAN, Aadhaar, and Demat account detection directly in the inference pipeline.
2. **Numerical Hallucination Control**: Cross-checks numbers against context to prevent confidently hallucinated percentages.
3. **Compliance Phrase Detection**: Instantly flags SEBI/RBI violations (e.g. `"risk-free"`, `"guaranteed returns"`).
4. **Optimized CPU Performance**: Native ONNX integration provides **sub-150ms** latency without a GPU.

## Quick Start (Plug-and-Play)

FinGuard is "Optimized by Default". No complex hardware configuration required.

### 1. Installation
```bash
pip install finguard
```

### 2. Wrap your LLM
```python
import asyncio
from finguard import FinGuard

# 1. Initialize guard with a built-in policy (Wealth Mgmt, Banking, or Fraud)
guard = FinGuard(policy="wealth_mgmt_assistant_v1")

# 2. Wrap your async LLM call
@guard.wrap
async def chatbot_reply(prompt: str) -> str:
    return await my_llm_client.chat(prompt)

# 3. Use it! Everything is scanned asynchronously with ONNX acceleration.
async def main():
    try:
        response = await chatbot_reply("What mutual fund guarantees 20% returns?")
        print(response)
    except Exception as e:
        print(f"FinGuard Intercepted: {e}")

asyncio.run(main())
```

## 🚀 Performance

FinGuard v0.2.0 uses **ONNX Runtime** by default, providing **sub-150ms** latency for full-stack financial safety checks on standard CPU hardware.

| Runtime | Device | Latency (p50) | Status |
| :--- | :--- | :--- | :--- |
| Standard (v0.1) | CPU | ~400 ms | Deprecated |
| **Optimized** (v0.2) | **CPU (ONNX)** | **117 ms** | **Active** |

## Documentation

- [📘 General User Guide](docs/user_guide.md)
- [⚙️ Creating Custom YAML Policies](docs/custom_policies.md)

---
*Built openly for the financial AI community.*
