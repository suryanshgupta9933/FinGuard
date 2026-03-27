# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1] - 2026-03-28

### Added
- **Environment Health Check**: New `check_runtime_health()` utility to verify ONNX availability at startup. FinGuard now warns users loudly with fix instructions if `onnxruntime` or `optimum` are missing.
- **Model Pre-fetching**: New `finguard-download` CLI command and `FinGuard.download_models()` method to pre-cache all ONNX models, eliminating first-run latency.

### Fixed
- **Silent Latency Regression**: Fixed a bug where scanners would silently fall back to slow PyTorch inference without notifying the user.
- **Environment Stability**: Pinned `numpy < 2.0.0` and `torch >= 2.2.0` to resolve critical initialization crashes and `rms_norm` attribute errors in fresh environments.
- **Pipeline Redaction**: Corrected the output pipeline to properly recognize and persist PII redactions from the native `FinGuardPIIEngine`.

## [0.3.0] - 2026-03-28

## [0.2.0] - 2026-03-27

### Added
- **Native ONNX Acceleration**: Forced ONNX Runtime by default for all scanners, achieving a 3.4x performance gain on CPU.
- **Sub-150ms Latency**: Reduced baseline scanning overhead from ~400ms to ~117ms natively.
- **`FinGuard` Schema Refactor**: Extracted data models into `finguard/schema.py` to resolve circular dependencies and improve maintainability.

### Changed
- **Unified API**: Simplified `FinGuard` constructor by removing `device` auto-detection logic. The framework is now "Fast-by-default" on all platforms.
- **Dependency Stabilization**: Capped Python version to `<3.13` and optimized the core `onnxruntime` and `optimum` stack.
- **Refined Logging**: Suppressed noisy external library logs (transformers, hf_hub) and streamlined hardware status reports.

### Removed
- Experimental GPU/CUDA auto-detection (transitioned to universal high-speed CPU-ONNX architecture for stability).

### Fixed
- Initialization bug where `llm-guard` would force CUDA providers even if ORT-GPU was missing.
- Circular import between `core.py` and `pipeline.py`.
