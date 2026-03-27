import logging
import onnxruntime
from typing import List, Any
from llm_guard.input_scanners import PromptInjection, BanTopics

# Module-level state for cleaner DX
_HARDWARE_LOGGED = False

def _setup_onnx_logging():
    global _HARDWARE_LOGGED
    if not _HARDWARE_LOGGED:
        for logger_name in ["transformers", "huggingface_hub", "onnxruntime"]:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
        print("[FinGuard Info] Using Optimized CPU Runtime (ONNX).")
        _HARDWARE_LOGGED = True

def get_input_scanners(risk_level: str, policy: Any) -> List[Any]:
    _setup_onnx_logging()
    scanners = []
    
    # We default to ONNX-CPU for high performance (3.4x v0.1)
    use_onnx = True

    if policy.injection:
        if PromptInjection:
            scanners.append(PromptInjection(threshold=policy.injection.threshold, use_onnx=use_onnx))
            
    if policy.topic_boundary and policy.topic_boundary.enabled:
        if BanTopics:
            scanners.append(BanTopics(
                topics=policy.topic_boundary.banned_topics, 
                threshold=0.75,
                use_onnx=use_onnx
            ))
            
    return scanners

def get_output_scanners(risk_level: str, policy: Any) -> List[Any]:
    from .validators.numerical import NumericalClaimValidator
    from .validators.compliance import CompliancePhraseDetector
    from .validators.regulatory import RegulatoryContextTagger
    
    scanners = []
    
    # Financial specific validators
    if policy.output:
        if policy.output.numerical_validation:
            scanners.append(NumericalClaimValidator())
            
        if policy.output.compliance_phrases:
            scanners.append(CompliancePhraseDetector(disclaimers=policy.output.required_disclaimers))

    # Add tagger for all paths
    scanners.append(RegulatoryContextTagger())
    
    return scanners
