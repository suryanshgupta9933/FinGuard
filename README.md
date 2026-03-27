# FinGuard 🛡️

**The High-Performance LLM Safety Layer for Financial AI.**

FinGuard is a modular, enterprise-grade guardrail framework designed specifically for fintech and wealth management teams. It provides a secure bridge between powerful LLMs and the rigorous compliance requirements of the financial industry.

## 🚀 Why FinGuard?

*   **Elite Performance**: Sub-400ms latency for full-stack audits (PII + Injection + Compliance) using optimized ONNX-CPU inference.
*   **Modular Tiers**: Choose between **Turbo** (Regex/Instant), **Fast** (ONNX), and **Enterprise** (NER) safety paths.
*   **Advice-Aware Compliance**: Intelligently detects financial advice vs. banking operations to minimize false positives.
*   **PII Vault & Redaction**: Native support for stateful PII anonymization and response redaction.
*   **Financial Specialists**: Built-in validators for Indian Financial Identifiers (PAN, Aadhaar, IFSC, VPA) and PMLA compliance.

## 🚀 Launch Demo

Test FinGuard instantly in your browser:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/protectai/finguard/blob/main/notebooks/FinGuard_Demo.ipynb)

## 🎭 User Personas & Scenarios

FinGuard adapts its safety posture based on the user's role. See the `examples/demo.py` for implementation.

| Persona | Scenario | Safety Action |
| :--- | :--- | :--- |
| **Casual Banker** | Accidental Aadhaar leak in prompt | **BLOCK** (Fast-Path Regex) |
| **Wealth Manager**| Investment advice without disclaimer | **BLOCK** (Compliance Check) |
| **Compliance Officer**| Transfer ₹1,000,000 | **BLOCK** (PMLA Enforcement) |
| **Security Analyst** | Prompt Injection attempt | **BLOCK** (ONNX AI-Fast) |

## 🏗️ Performance Tiers

| Tier | Latency (Avg) | Safety Modules | Use Case |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Instant)** | < 10ms | Regex PII, PMLA, IFSC/PAN | Local, low-compute environments |
| **Tier 2 (Fast AI)** | < 150ms | ONNX Prompt Injection, Topic Detection | Standard chatbot security |
| **Tier 3 (Enterprise)**| < 400ms | Deep NER PII (Presidio), Hallucination | Production-grade financial apps |

## 🛠️ Performance Features (v0.2.0)

### 1. Granular Latency Tracking
Every `GuardResult` now contains a `component_latencies` map. Identify bottlenecks instantly:
```python
res = await guard(prompt, llm_fn)
print(res.component_latencies)
# {'Anonymize': 176.0ms, 'PromptInjection': 35.6ms, 'BanTopics': 79.9ms, ...}
```

### 2. Output PII Redaction
Prevent the LLM from leaking sensitive customer data back to the user:
```yaml
# policy.yaml
pii:
  enabled: true
  entities: ["EMAIL_ADDRESS", "PHONE_NUMBER"]
  redact_output: true
```

### 3. Indian Financial "Fast Path"
Ultra-fast detection for regional identifiers using the `IndianFinancialPII` scanner.
- **PAN**: `ABCDE1234F`
- **Aadhaar**: `1234 5678 9101`
- **IFSC**: `SBIN0001234`
- **VPA/UPI**: `user@okbank`

## 📋 Policy Catalog

FinGuard comes with a set of pre-configured, domain-specialized policies that can be loaded by name:

| Policy ID | Best For | Safety Level |
| :--- | :--- | :--- |
| `retail_banking_turbo` | Retail bots where <10ms speed is required | Medium |
| `wealth_mgmt_assistant_v1`| Investment advice with deep NER & Compliance | High |
| `compliance_officer_strict`| High-risk operations and PMLA enforcement | Critical |
| `fraud_ops_agent_v1` | Backend fraud analysis with strict PII protection | Critical |

```python
# Load by name automatically from finguard/policies/
guard = FinGuard(policy="retail_banking_turbo")
```

## 📖 Quick Start

```python
from finguard import FinGuard

# Force Turbo Mode (Fast PII only)
guard = FinGuard(policy={
    "pii": {"enabled": True, "fast_pii_only": True},
    "injection": {"enabled": True}
})

@guard.wrap
async def wealth_assistant(prompt: str):
    return await llm.generate(prompt)

# Returns redacted or blocked response
response = await wealth_assistant("My PAN is ABCDE1234F")
```

## 📊 Benchmarking
Run the refined benchmark suite to verify your environment's performance:
```bash
uv run benchmark.py
```

## ⚖️ License
MIT License. Optimized for production-ready financial AI.
