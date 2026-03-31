# Installation & Setup

Protecting your agentic LLM workflows takes less than 2 minutes. 

## Requirements
FinGuard is built for modern asynchronous Python.
- Python 3.10+
- `uv` or `pip`

## 1. Quick Install

Install the core framework. FinGuard uses highly optimized ONNX runtimes dynamically managed at startup, so the base install is surprisingly light.

```bash
pip install finguard
```

## 2. Enterprise Extras (Recommended)

If you are running in production and need either Langfuse or OpenTelemetry APM integrations, install the observability extra:

```bash
pip install "finguard[observability]"
```

For contributors, the `[all]` extra pulls in everything including MkDocs material tools:

```bash
pip install "finguard[all]"
```

## 3. Verify Health

Once installed, we recommend pre-downloading the ONNX models so your container boots instantly in production without attempting network calls.

```python
from finguard import FinGuard

# Downloads ~300MB of ONNX weights to ~/.cache/huggingface
FinGuard.download_models()
```
