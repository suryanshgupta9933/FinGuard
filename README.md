# FinGuard 🛡️

**The LLM Safety Orchestration Layer for Financial AI.**

FinGuard is a modular, plug-and-play guardrail framework built for fintech teams. It wraps any LLM with a tiered safety pipeline covering PII redaction, prompt injection detection, regulatory compliance, and financial fraud signals — all configurable via simple YAML policies.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/arupmahatha/FinGuard/blob/main/notebooks/FinGuard_Demo.ipynb)

---

## ⚡ Quick Start

```python
from finguard import FinGuard

guard = FinGuard(policy="retail_banking")

@guard.wrap
async def banking_assistant(prompt: str) -> str:
    return await llm.generate(prompt)

# PAN card in prompt is automatically blocked
response = await banking_assistant("My PAN is ABCDE1234F, reset my password")
```

---

## 🏗️ Tiered Safety Architecture

FinGuard uses a **three-tier pipeline** — each tier adds safety depth at the cost of latency. Pick the tier that fits your use case.

| Tier | Policy | Avg Latency | What It Covers |
| :--- | :--- | :--- | :--- |
| **Tier 1 — Fast Lane** | `fast_lane` | ~35ms | Regex PII (PAN, Aadhaar, IFSC, UPI), PMLA |
| **Tier 2 — Standard** | `retail_banking`, `default` | ~55ms | Tier 1 + Native Presidio NER + Injection AI |
| **Tier 3 — Full Stack** | `high_security`, `wealth_advisor` | ~180ms | Tier 2 + Topic Banning + Compliance Phrases |

> **Benchmarks** measured on CPU (ONNX runtime, no GPU). Mock LLM latency excluded.

---

## 📋 Policy Catalog

FinGuard ships with 5 ready-to-use policies. Load by name:

```python
guard = FinGuard(policy="high_security")
```

| Policy | Use Case | Tier |
| :--- | :--- | :--- |
| `default` | Balanced starting point for any financial bot | 2 |
| `fast_lane` | High-throughput systems: IVR, SMS bots, dashboards | 1 |
| `retail_banking` | Branch chatbots, net banking, UPI assistants | 2 |
| `wealth_advisor` | Robo-advisors, portfolio managers (SEBI compliance) | 3 |
| `high_security` | Fraud ops, compliance officers, internal audit tools | 3 |

All policies ship with `injection.threshold: 1.0` — only absolute certainty triggers a block.

---

## 🔍 What Gets Protected

### PII — Finance Base (Always Active)
Native [Presidio](https://microsoft.github.io/presidio/) entities with context-awareness and checksum validation:

| Entity | ID | Detection |
| :--- | :--- | :--- |
| Credit Card | `CREDIT_CARD` | Pattern + Luhn checksum |
| IBAN | `IBAN_CODE` | Pattern + checksum |
| PAN Card | `IN_PAN` | Pattern + context |
| Aadhaar | `IN_AADHAAR` | Pattern + Verhoeff checksum |
| IFSC Code | `IN_IFSC` | Custom pattern + context |
| UPI/VPA | `IN_VPA` | Custom pattern + context |
| Email / Phone | `EMAIL_ADDRESS`, `PHONE_NUMBER` | Pattern |

### Optional Locale Packs
```yaml
pii:
  locale_packs: ["IN_EXTENDED"]  # Adds Voter ID, Passport, Vehicle Reg
  # locale_packs: ["US"]         # Adds SSN, Driver License
  # locale_packs: ["GLOBAL"]     # Adds IP, URL, Location
```

### Fraud & Compliance
- **PMLA Scanner** — flags high-value transfers (>₹50,000) with transfer keywords
- **Compliance Phrases** — enforces SEBI/RBI-style disclaimers on investment advice
- **Numerical Hallucination** — validates AI-stated figures against prompt context
- **Topic Banning** — blocks off-domain queries (crypto, medical, illegal lending)

---

## 🧩 Architecture

```
Prompt → [Tier 1: Regex Fast-Path] → [Tier 2: Presidio NER + ONNX AI] → [Tier 3: Compliance] → LLM → Output Guard → Response
```

- **Singleton model cache** — ONNX models loaded once per process, shared across all guards
- **Whitelist-only PII registry** — only finance-relevant recognizers are active; no BTC/SSN overhead
- **Per-component latency** — every `GuardResult` exposes `component_latencies` for observability

---

## 📊 Benchmarking

```bash
uv run benchmark.py
```

Sample output:
```
══════════════════════════════════════════════════════════════
  BENCHMARK SUMMARY
══════════════════════════════════════════════════════════════
  Tier                                     Avg      Min      Max
  Tier 1 – Fast Lane  (Regex)            35.0ms   30.5ms   36.9ms
  Tier 2 – Retail     (NER+AI)           54.7ms   47.3ms   65.4ms
  Tier 3 – High Sec   (Full)            181.0ms  149.2ms  277.3ms
══════════════════════════════════════════════════════════════
```

---

## 📁 Project Structure

```
finguard/
├── pii/                   # Native Presidio PII engine
│   ├── engine.py          # FinGuardPIIEngine singleton
│   ├── profiles.py        # Finance base + locale packs
│   └── recognizers.py     # Custom recognizers (IFSC, VPA, Demat)
├── validators/            # Domain-specific validators
│   ├── financial.py       # Fast-path regex + PMLA scanner
│   ├── compliance.py      # Disclaimer enforcement
│   └── numerical.py       # Hallucination detection
├── policies/              # YAML policy catalog
│   ├── default.yaml
│   ├── fast_lane.yaml
│   ├── retail_banking.yaml
│   ├── wealth_advisor.yaml
│   └── high_security.yaml
├── core.py                # FinGuard main class
├── router.py              # Scanner factory + model cache
└── config.py              # Pydantic policy models
```

---

## ⚖️ License

MIT License.
