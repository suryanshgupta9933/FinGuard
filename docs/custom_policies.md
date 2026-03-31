# Custom YAML Policies

FinGuard policies are YAML files that define your safety posture. They can be loaded by name (from the built-in catalog) or by file path.

## Policy Schema

```yaml
policy_id: my_financial_bot_v1
risk_level: medium  # low | medium | high

pii:
  enabled: true
  fast_pii_only: false      # true = regex only (<35ms), false = full Presidio NER (~55ms)
  locale_packs: []           # Optional: ["IN_EXTENDED", "US", "UK", "GLOBAL"]
  extra_entities: []         # Add any Presidio entity ID
  exclude_entities: []       # Remove entities from the finance base
  redact_output: false       # Also redact PII in LLM responses

injection:
  enabled: true
  threshold: 1.0             # 1.0 = only block on absolute certainty (recommended)

topic_boundary:
  enabled: false
  banned_topics:
    - crypto_trading
    - medical_advice
    - unstructured_loans

output:
  numerical_validation: false
  compliance_phrases: false
  required_disclaimers:
    - "This is not personalized investment advice."
  on_fail: block

audit:
  backend: "memory"          # "memory" | "file" | "langfuse" | "otel"
  emit_traces: true
  redact_input: true         # uses SHA-256 for prompt inputs instead of raw text
  file_path: "logs/finguard_%Y-%m-%d.ndjson"  # only if backend="file"
  include_metadata_keys: []  # e.g., ["session_id", "user_id"]
```

## Finance Base (Always Active)

The following entities are always scanned regardless of `locale_packs`:

| Entity | ID |
| :--- | :--- |
| PAN Card | `IN_PAN` |
| Aadhaar | `IN_AADHAAR` |
| IFSC Code | `IN_IFSC` (custom) |
| UPI/VPA | `IN_VPA` (custom) |
| Credit Card | `CREDIT_CARD` |
| IBAN | `IBAN_CODE` |
| Email / Phone | `EMAIL_ADDRESS`, `PHONE_NUMBER` |

## Locale Packs

```yaml
pii:
  locale_packs:
    - IN_EXTENDED  # Voter ID, Passport, Vehicle Registration
    - US           # SSN, Driver License
    - UK           # NHS, NINO
    - GLOBAL       # IP, URL, Location, Date
```

## Loading Policies

```python
# By name (from finguard/policies/)
guard = FinGuard(policy="retail_banking")

# By file path
guard = FinGuard(policy="./path/to/my_policy.yaml")

# Inline dict
guard = FinGuard(policy={
    "pii": {"enabled": True, "fast_pii_only": True},
    "injection": {"enabled": True, "threshold": 1.0}
})
```
