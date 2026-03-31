# Protection Policies

Financial AI requires deterministic rule enforcement, but hard-coding those rules across 50 API microservices is an anti-pattern. 

FinGuard decouples **Rules** from **Code** via simple `.yaml` files. A single policy dictates the entire orchestration cycle for an Agent or API route.

## The Global Config Schema

A FinGuard Policy is composed of 5 discrete configuration blocks. Un-configured blocks simply drop out of the orchestration pipeline natively.

```yaml
policy_id: "global_secure_agent"
risk_level: "high"               # "low" | "medium" | "high"  (Dictates default thresholds)

pii:
  enabled: true
  action: anonymize              # Or "block"
  redact_output: true
  locale_packs: ["UK", "US"]
  
injection:
  enabled: true
  engine: llm_guard
  threshold: 0.85
  
tools:
  enabled: true
  allowed: ["read_db", "fetch_market_prices"]
  max_calls_per_session: 15
  require_approval_above_risk: 2 # Integrates human-in-the-loop

audit:
  emit_traces: true
  backend: langfuse              # Or "otel", "memory", "file"
  redact_input: true             # SHA-256 hashes prompts for SOC2 compliance

output:
  on_fail: block
  numerical_validation: true     # Cross-checks numbers against prompt context
  required_disclaimers:
    - "This AI is not a registered financial advisor."
```

## Built-In Policies

FinGuard ships with 5 expertly tuned profiles depending on your infrastructure:
- `default.yaml` - Standard safety (Moderate PII, strict injection protection).
- `fast_lane.yaml` - Skips NER for <10ms latencies (Only uses fast-path regex).
- `retail_banking.yaml` - Strict PII detection for customer-facing chatbots.
- `wealth_advisor.yaml` - High limits for numerical extraction.
- `high_security.yaml` - Maximum agent isolation, strict tool blocking.

```python
from finguard import FinGuard

# Use a built-in simply by referencing its name
guard = FinGuard(policy="retail_banking")
```

## Custom Policies

For custom rules, pass a dictionary directly or link to your own absolute path YAML. This is ideal when pulling dynamically from a Vault or Parameter Store.

```python
import yaml
import boto3

# Fetch from S3/Parameter Store
raw_yaml = get_policy_from_aws()
policy_dict = yaml.safe_load(raw_yaml)

guard = FinGuard(policy=policy_dict)
```
