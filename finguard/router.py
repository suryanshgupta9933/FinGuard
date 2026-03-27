import logging
import onnxruntime
import time
from typing import List, Any, Dict, Tuple
from llm_guard.input_scanners import PromptInjection, BanTopics, Anonymize
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
        # Aggressive silence for production
        loggers = [
            "transformers", "huggingface_hub", "onnxruntime", 
            "presidio_analyzer", "presidio_anonymizer",
            "presidio_analyzer.recognizer_registry",
            "presidio_analyzer.app",
            "presidio_analyzer.ner_model_configuration"
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
    # Create hashable versions of lists for the cache key
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
        # Pass the original kwargs to the constructor
        _SCANNER_CACHE[cache_key] = cls(**kwargs)
        
    return _SCANNER_CACHE[cache_key]

def get_input_scanners(risk_level: str, policy: Any, vault: Any = None) -> List[Any]:
    from .validators.financial import IndianFinancialPII, PMLAScanner
    scanners = []
    use_onnx = True

    # 1. Fast Path Financial PII (Regex) - Sub 1ms
    if policy.pii and policy.pii.enabled:
        scanners.append(IndianFinancialPII(entities=policy.pii.entities))

    # 2. Heavy NER PII (Presidio)
    if policy.pii and policy.pii.enabled and policy.pii.engine == "presidio" and not policy.pii.fast_pii_only:
        v = vault or get_vault()
        # Pass a LIST to Anonymize (llm-guard modifies it in-place)
        scanners.append(get_cached_scanner(Anonymize, vault=v, entity_types=list(policy.pii.entities)))

    # 3. PMLA / High-Value Transfer Detection
    scanners.append(PMLAScanner())

    # 4. AI-Based Scanners (ONNX Cached)
    if policy.injection and policy.injection.enabled:
        scanners.append(get_cached_scanner(PromptInjection, threshold=policy.injection.threshold, use_onnx=use_onnx))
            
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
    from .validators.regulatory import RegulatoryContextTagger
    
    scanners = []
    
    if policy.output:
        if policy.output.numerical_validation:
            scanners.append(NumericalClaimValidator())
        if policy.output.compliance_phrases:
            scanners.append(CompliancePhraseDetector(disclaimers=policy.output.required_disclaimers))

    if policy.pii and policy.pii.enabled and policy.pii.redact_output:
        v = get_vault()
        scanners.append(get_cached_scanner(Anonymize, vault=v, entity_types=list(policy.pii.entities)))

    scanners.append(RegulatoryContextTagger())
    return scanners
