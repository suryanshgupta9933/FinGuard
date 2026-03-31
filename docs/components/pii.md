# PII Anonymization Engine

A critical requirement for financial AI is protecting Indian PAN cards, Aadhar numbers, US SSNs, and banking traces from ever reaching external LLM providers (like OpenAI or Anthropic).

## Presidio + Fast-Path Backend

FinGuard ships with a hyper-optimized PII pipeline (`FinGuardPIIEngine`) that runs natively on your CPU. It blends Microsoft Presidio's NER (Named Entity Recognition) models with direct high-speed Regex for strict financial identifiers.

We decouple the entity rules from your python orchestration loop:

```yaml
# policy.yaml
pii:
  enabled: true
  action: anonymize 
  locale_packs: ["IN_EXTENDED", "US"]
```

## Mandatory Finance Base

No matter your locale, FinGuard always loads the **Finance Base Entities**:
- `CREDIT_CARD`, `IBAN_CODE`
- `EMAIL_ADDRESS`, `PHONE_NUMBER`
- Default Market (Indian Finance): `IN_PAN`, `IN_AADHAAR`, `IN_IFSC`, `IN_VPA`, `IN_DEMAT`, `IN_BANK_ACCOUNT`

## Locale Packs

If you are operating in other regions or need extended identification, simply add a string to your `locale_packs` array in `policy.yaml`:

- **`IN_EXTENDED`**: Detects Indian Voter IDs, Passports, and Vehicle Registrations.
- **`US`**: Detects US Social Security Numbers, ITINs, and Driver's Licenses.
- **`UK`**: Detects NHS numbers and UK National Insurance Numbers.
- **`GLOBAL`**: Broadly detects IP Addresses, standard Locations, Date/Times, and URLs.

*Note: Enabling `GLOBAL` or `IN_EXTENDED` activates additional NER transformer passes which may increase latency by ~20ms.*

## Actions

The `action` parameter dictates what FinGuard does when it finds PII in the prompt going to the LLM.

- `anonymize`: Rewrites the string and preserves contextual length (e.g., `My PAN is ABCDE1234F` natively becomes `My PAN is <IN_PAN>`).
- `block`: Halts execution natively, raising a `FinGuardViolation`, returning a safe rejection directly to the agent without triggering the LLM.

## Bi-Directional Coverage (Output Redaction)

Data leaks happen on the way **out** too. An agent with internal database readout permissions could easily be tricked via prompt injection into printing a client's plaintext account balance to a chat screen.

```yaml
pii:
  enabled: true
  action: anonymize
  redact_output: true
```

By setting `redact_output: true`, FinGuard intercepts the LLM's response before standard return. It initiates a second `FinGuardPIIEngine` scanning pass and scrubs the outbound string, so the end-user never sees the breached data!
