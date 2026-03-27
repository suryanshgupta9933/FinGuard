# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-03-28

### Changed
- **Documentation**: Updated `memory.MD` with a complete API Context Map reflecting the modern 3-Tier architecture and core modules.
- **Tests**: Replaced deprecated policies (`banking_support_chatbot_v1`, `wealth_mgmt_assistant_v1`) in the test suite with updated catalog entries (`retail_banking`, `wealth_advisor`).

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
