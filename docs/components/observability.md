# Enterprise Observability

Security layers are blind without world-class auditory integrations. FinGuard shifts away from basic print statements to providing 100% forensic reconstructability via `GuardTrace`.

Whenever an LLM Pipeline is executed or a Tool is called, an immutable `GuardTrace` UUID is generated.

## Langfuse Integration

Langfuse provides incredible UI visualization for multi-turn Agent flows. FinGuard natively streams its structured violations as hierarchical Spans within Langfuse traces.

```yaml
# policy.yaml
audit:
  emit_traces: true
  backend: langfuse
  redact_input: true # Hashes prompts via SHA-256 for GDPR compliance
```

### Trace Hierarchies & Scoring
If your Agent passes a `session_id` inside the `GuardRequest(metadata={"session_id": "123"})`, FinGuard will dynamically attach its spans to the active Langfuse Session group.

When FinGuard blocks an AI action, it emits a `Score` to Langfuse with `{ "name": "prompt_injection", "value": 1.0 }`. This allows CISOs to instantly filter their Langfuse dashboards for "Blocked Generative AI Traffic".

## OpenTelemetry (DataDog, Jaeger, Honeycomb)

If your enterprise uses a standard OTEL collector:

```yaml
# policy.yaml
audit:
  emit_traces: true
  backend: otel
```

FinGuard generates standard distributed traces `(opentelemetry.trace)`. It creates a main Span named `finguard.guard` enriched with attributes like `finguard.policy_id` and `finguard.action`. Each individual underlying scanner (like PII or Injection) emits its own child Span, allowing you to track PII latency down to the micro-second in Jaeger.

FinGuard also exposes two primary metrics `(opentelemetry.metrics)`:
- `finguard.latency.ms` (Histogram)
- `finguard.violations.count` (Counter)

## Memory & Native JSON File Backends

If you are developing locally, you don't need heavyweight cloud collectors.

```yaml
# policy.yaml
audit:
  backend: file
  file_path: "logs/finguard_%Y-%m-%d.ndjson"
```

The `file` backend dynamically rotates logs into a highly queryable NDJSON format. The default `memory` backend keeps the last 1,000 traces in a rapid LRU buffer for local CLI queries!
