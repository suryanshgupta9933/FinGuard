# Custom YAML Policies

FinGuard allows extensive customization without writing boilerplate Python code. You can define your own rules in a `.yaml` file and pass its path to the `FinGuard` constructor.

## Structure of a Policy File

A standard policy file contains blocks for `pii`, `topic_boundary`, and `output`.

```yaml
policy_id: custom_finance_rules_v1
risk_level: medium

pii:
  engine: presidio
  entities: [IN_PAN, IN_AADHAAR, CREDIT_CARD]
  action: anonymize # Options: anonymize, block

topic_boundary:
  enabled: true
  banned_topics: 
    - medical_advice
    - crypto_trading
    - political_opinions

output:
  numerical_validation: true  # Prevents numerical hallucinations
  compliance_phrases: custom
  required_disclaimers: 
    - "This is not personalized investment advice."
  on_fail: block  # Options: block, warn, fix

audit:
  backend: json
  retention_days: 180
```

## Using Custom YAML

To use your custom YAML:

```python
from finguard import FinGuard

# Pass the absolute or relative path to your YAML file
guard = FinGuard(policy="./path/to/my_custom_policy.yaml")

@guard.wrap
async def generate(prompt: str):
    pass
```

## Key Properties

- **`pii.entities`**: Specify the exact entities you want to scrub. FinGuard includes custom Indian entities like `IN_PAN` and `IN_AADHAAR`.
- **`topic_boundary.banned_topics`**: Provide a list of semantic topics the LLM should refuse to engage with.
- **`output.numerical_validation`**: Set to `true` to cross-check numbers in the output against the prompt, mitigating hallucinated return rates.
- **`output.required_disclaimers`**: Ensures the LLM appended these specific strings before returning the response. If missing, it triggers a violation.
