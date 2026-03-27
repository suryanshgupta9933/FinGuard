import logging
import onnxruntime
import time
from typing import List, Any, Dict, Tuple
from llm_guard.input_scanners import PromptInjection, BanTopics
from llm_guard.vault import Vault

# --- Module-level Singleton Registry ---
_SCANNER_CACHE: Dict[Tuple[str, str], Any] = {}
_HARDWARE_LOGGED = False
_VAULT = None

def get_vault():
    global _VAULT
    if _VAULT is None:
        _VAULT = Vault()
    return _VAULT

def _setup_onnx_logging():
    global _HARDWARE_LOGGED
    if not _HARDWARE_LOGGED:
        loggers = [
            "transformers", "huggingface_hub", "onnxruntime", 
            "presidio_analyzer", "presidio_anonymizer",
            "presidio_analyzer.recognizer_registry",
            "presidio_analyzer.app",
            "presidio_analyzer.ner_model_configuration",
            "presidio-analyzer",  # Silences 'Recognizer not added' warnings
        ]
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.CRITICAL)
            logger.propagate = False
        print("[FinGuard Info] Using Optimized CPU Runtime (ONNX).")
        _HARDWARE_LOGGED = True

def get_cached_scanner(cls, **kwargs):
    """
    Returns a cached scanner instance or creates a new one if not found.
    Models are loaded exactly once per scanner configuration.
    """
    cache_kwargs = {}
    for k, v in kwargs.items():
        if isinstance(v, list):
            cache_kwargs[k] = tuple(v)
        else:
            cache_kwargs[k] = v
    config_str = str(sorted(cache_kwargs.items()))
    cache_key = (cls.__name__, config_str)
    if cache_key not in _SCANNER_CACHE:
        _setup_onnx_logging()
        _SCANNER_CACHE[cache_key] = cls(**kwargs)
    return _SCANNER_CACHE[cache_key]

def get_pii_scanner(policy: Any):
    """
    Returns the appropriate PII scanner based on policy config.
    
    fast_pii_only=True → lightweight regex-only Fast-Path (Tier 1)
    Otherwise         → full native Presidio engine (Tier 3)
    """
    from .pii import get_pii_engine
    if policy.pii and policy.pii.fast_pii_only:
        from .validators.financial import IndianFinancialPII
        return IndianFinancialPII()  # Tier 1: sub-1ms regex
    if policy.pii and policy.pii.enabled:
        return get_pii_engine(
            locale_packs=policy.pii.locale_packs or [],
            extra_entities=policy.pii.extra_entities or [],
            exclude_entities=policy.pii.exclude_entities or [],
        )
    return None


# PromptInjection: load the ONNX model exactly once, apply threshold at scan time.
_PROMPT_INJECTION_MODEL = None

class PromptInjectionWrapper:
    """Wraps a cached PromptInjection model, applying a per-policy threshold."""
    def __init__(self, model, threshold: float):
        self._model = model
        self.threshold = threshold
    
    def scan(self, prompt: str) -> tuple:
        # Run the underlying scanner but use our threshold
        _, is_valid, risk_score = self._model.scan(prompt)
        if risk_score >= self.threshold:
            return prompt, False, risk_score
        return prompt, True, risk_score

def get_cached_injection_scanner(threshold: float, use_onnx: bool = True):
    """Returns a threshold-aware wrapper sharing one underlying ONNX model."""
    global _PROMPT_INJECTION_MODEL
    if _PROMPT_INJECTION_MODEL is None:
        _setup_onnx_logging()
        _PROMPT_INJECTION_MODEL = PromptInjection(threshold=0.5, use_onnx=use_onnx)
    return PromptInjectionWrapper(_PROMPT_INJECTION_MODEL, threshold)

def get_input_scanners(risk_level: str, policy: Any, vault: Any = None) -> List[Any]:
    from .validators.financial import PMLAScanner
    _setup_onnx_logging()
    scanners = []
    use_onnx = True

    # 1. PII Scanner (Tier 1 or Tier 3 depending on fast_pii_only flag)
    pii_scanner = get_pii_scanner(policy)
    if pii_scanner:
        scanners.append(pii_scanner)

    # 2. PMLA / High-Value Transfer Detection (always fast, regex-based)
    scanners.append(PMLAScanner())

    # 3. AI-Based Scanners (ONNX Cached)
    if policy.injection and policy.injection.enabled:
        # Share ONE underlying model; threshold applied at scan time
        scanners.append(get_cached_injection_scanner(
            threshold=policy.injection.threshold,
            use_onnx=use_onnx
        ))
    if policy.topic_boundary and policy.topic_boundary.enabled:
        scanners.append(get_cached_scanner(
            BanTopics,
            topics=tuple(policy.topic_boundary.banned_topics),
            threshold=0.75,
            use_onnx=use_onnx
        ))
    return scanners

def get_output_scanners(risk_level: str, policy: Any) -> List[Any]:
    from .validators.numerical import NumericalClaimValidator
    from .validators.compliance import CompliancePhraseDetector
    scanners = []

    if policy.output:
        if policy.output.numerical_validation:
            scanners.append(NumericalClaimValidator())
        if policy.output.compliance_phrases:
            scanners.append(CompliancePhraseDetector(disclaimers=policy.output.required_disclaimers))

    # Output redaction via native Presidio engine
    if policy.pii and policy.pii.enabled and policy.pii.redact_output:
        from .pii import get_pii_engine
        scanners.append(get_pii_engine(
            locale_packs=policy.pii.locale_packs or [],
            extra_entities=policy.pii.extra_entities or [],
            exclude_entities=policy.pii.exclude_entities or [],
        ))

    return scanners
