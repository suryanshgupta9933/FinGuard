import yaml
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os

class PiiConfig(BaseModel):
    enabled: bool = True
    # locale_packs: Optional locale extensions on top of the mandatory finance base.
    # Options: "IN_EXTENDED", "US", "UK", "GLOBAL"
    locale_packs: List[str] = Field(default_factory=list)
    # extra_entities: Any additional Presidio entity IDs to include
    extra_entities: List[str] = Field(default_factory=list)
    # exclude_entities: Entities to remove even from the finance base
    exclude_entities: List[str] = Field(default_factory=list)
    action: str = "anonymize"
    redact_output: bool = False
    fast_pii_only: bool = False  # Skip NER, use custom regex Fast-Path only

class InjectionConfig(BaseModel):
    enabled: bool = True
    engine: str = "llm_guard"
    threshold: float = 0.75
    high_risk_fallback: Optional[str] = None

class TopicBoundaryConfig(BaseModel):
    enabled: bool = False
    banned_topics: List[str] = Field(default_factory=list)
    model: Optional[str] = None

class OutputConfig(BaseModel):
    numerical_validation: bool = False
    compliance_phrases: Optional[str | bool] = None
    required_disclaimers: List[str] = Field(default_factory=list)
    on_fail: str = "block" # block | reask | fix | warn

class AuditConfig(BaseModel):
    backend: str = "memory"
    """Trace backend: 'memory' | 'file' | 'console'"""
    
    file_path: str = "logs/finguard_%Y-%m-%d.ndjson"
    """Log file path when backend='file'. Supports strftime patterns for daily rotation."""
    
    emit_traces: bool = True
    """Set to False to completely disable GuardTrace assembly (minimal prod overhead)."""
    
    redact_input: bool = True
    """If True, stores SHA-256 fingerprint instead of raw prompt text. GDPR-safe."""
    
    include_metadata_keys: Optional[List[str]] = None
    """Allowlist of metadata keys to persist in trace. None means allow all."""
    
    retention_days: int = 30
    """Advisory retention period. Backends may use this for rotation logic."""
    
    trace_provider: Optional[str] = None
    """Future: 'langfuse' | 'otel' — reserved for v0.5 observability integrations."""


class ToolConfig(BaseModel):
    enabled: bool = False
    allowed: List[str] = Field(default_factory=list)
    blocked: List[str] = Field(default_factory=list)
    require_approval_above_risk: int = 3
    max_calls_per_session: int = 50

class PolicyConfig(BaseModel):
    policy_id: str = "custom_policy"
    risk_level: str = "low"
    pii: Optional[PiiConfig] = None
    injection: Optional[InjectionConfig] = None
    topic_boundary: Optional[TopicBoundaryConfig] = None
    output: Optional[OutputConfig] = None
    audit: Optional[AuditConfig] = None
    tools: Optional[ToolConfig] = None

    @classmethod
    def load(cls, policy: str | dict) -> 'PolicyConfig':
        """Loads a PolicyConfig from a dictionary, a file path, or returns as-is if already a PolicyConfig."""
        if isinstance(policy, cls):
            return policy
        if isinstance(policy, dict):
            return cls(**policy)
        if isinstance(policy, str):
            # Assume it's a path or a known preset
            preset_path = os.path.join(os.path.dirname(__file__), "policies", f"{policy}.yaml")
            
            if os.path.isfile(policy):
                path_to_load = policy
            elif os.path.isfile(preset_path):
                path_to_load = preset_path
            else:
                raise ValueError(f"Policy preset or file '{policy}' not found.")
                
            with open(path_to_load, "r") as f:
                data = yaml.safe_load(f)
            return cls(**data)
        
        raise TypeError(f"Invalid policy type: {type(policy)}")
