from typing import Any, List
# We'll use mocked fallbacks or generic imports for now to avoid hard failures
# if specific versions of llm_guard differ.
try:
    from llm_guard.input_scanners import PromptInjection, BanTopics
except ImportError:
    PromptInjection = None
    BanTopics = None

def get_input_scanners(risk_level: str, policy: Any) -> List[Any]:
    scanners = []
    
    if policy.injection:
        if PromptInjection:
            scanners.append(PromptInjection(threshold=policy.injection.threshold))
            
    if policy.topic_boundary and policy.topic_boundary.enabled:
        if BanTopics:
            # We assume allowed_topics means we ban everything ELSE, or we use a custom ban list
            # For simplicity in this skeleton, we just ensure it exists
            scanners.append(BanTopics(topics=policy.topic_boundary.banned_topics, threshold=0.75))
            
    if risk_level == "high":
        # high risk path adds heavier models like Llama Guard 3 locally
        pass
        
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
            # could load specific ruleset
            scanners.append(CompliancePhraseDetector(disclaimers=policy.output.required_disclaimers))

    # Add tagger for all paths
    scanners.append(RegulatoryContextTagger())
    
    return scanners
