"""
FinGuard Native Presidio PII Engine
Direct Presidio integration — finance is the mandatory base.
Replaces both `IndianFinancialPII` and `llm-guard`'s `Anonymize` wrapper.
"""
from __future__ import annotations
import logging
from typing import Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine

from .profiles import FINANCE_BASE_ENTITIES, LOCALE_PACKS
from .recognizers import build_custom_recognizers

# Singleton
_ENGINE_CACHE: dict[str, "FinGuardPIIEngine"] = {}

# Entities sourced natively from Presidio (no custom recognizer needed)
_PRESIDIO_NATIVE = {
    "CREDIT_CARD", "IBAN_CODE", "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
    "IN_PAN", "IN_AADHAAR", "IN_GSTIN", "IN_VOTER", "IN_PASSPORT",
    "IN_VEHICLE_REGISTRATION", "US_SSN", "US_ITIN", "US_DRIVER_LICENSE",
    "UK_NHS", "UK_NINO", "IP_ADDRESS", "LOCATION", "DATE_TIME", "URL",
}

# Native recognizer class names to keep (whitelist-based pruning)
_NATIVE_RECOGNIZER_MAP = {
    "CREDIT_CARD": "CreditCardRecognizer",
    "IBAN_CODE": "IbanRecognizer",
    "PERSON": None,          # Handled by the NER Transformer
    "EMAIL_ADDRESS": "EmailRecognizer",
    "PHONE_NUMBER": "PhoneRecognizer",
    "IN_PAN": "InPanRecognizer",
    "IN_AADHAAR": "InAadhaarRecognizer",
    "IN_GSTIN": "InGstinRecognizer",
    "IN_VOTER": "InVoterRecognizer",
    "IN_PASSPORT": "InPassportRecognizer",
    "IN_VEHICLE_REGISTRATION": "InVehicleRegistrationRecognizer",
    "US_SSN": "UsSsnRecognizer",
    "US_ITIN": "UsItinRecognizer",
    "US_DRIVER_LICENSE": "UsLicenseRecognizer",
    "UK_NHS": "NhsRecognizer",
    "UK_NINO": "UkNinoRecognizer",
    "IP_ADDRESS": "IpRecognizer",
    "LOCATION": None,        # Handled by NER
    "DATE_TIME": "DateRecognizer",
    "URL": "UrlRecognizer",
}


class FinGuardPIIEngine:
    """
    Native Presidio-based PII engine for FinGuard.
    
    Finance is the mandatory base. Additional locale packs can be enabled
    via the `locale_packs` parameter. Custom entities can be added via
    `extra_entities`.
    """

    def __init__(
        self,
        locale_packs: list[str] | None = None,
        extra_entities: list[str] | None = None,
        exclude_entities: list[str] | None = None,
    ):
        # Resolve active entity set
        active_entities = set(FINANCE_BASE_ENTITIES)
        for pack in (locale_packs or []):
            active_entities.update(LOCALE_PACKS.get(pack, []))
        if extra_entities:
            active_entities.update(extra_entities)
        if exclude_entities:
            active_entities.difference_update(exclude_entities)
        
        self._active_entities = list(active_entities)
        
        # 1. Build whitelist-only registry
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(languages=["en"])
        
        # 2. Prune to active entity whitelist
        active_recognizer_names = {
            _NATIVE_RECOGNIZER_MAP[e] for e in active_entities
            if e in _NATIVE_RECOGNIZER_MAP and _NATIVE_RECOGNIZER_MAP[e] is not None
        }
        for r in list(registry.recognizers):
            # Always keep Transformers NER and PatternRecognizers from llm-guard
            if "Transformers" in r.name or "PatternRecognizer" in r.name:
                continue
            if r.name not in active_recognizer_names:
                try:
                    registry.remove_recognizer(r.name)
                except Exception:
                    pass
        
        # 3. Add custom recognizers for entities not covered by Presidio
        custom_recognizers = build_custom_recognizers()
        for rec in custom_recognizers:
            if rec.supported_entities[0] in active_entities:
                registry.add_recognizer(rec)

        # 4. Initialize engines (single-pass, no llm-guard wrapper)
        self._analyzer = AnalyzerEngine(registry=registry)
        self._anonymizer = AnonymizerEngine()
        
        # Silence internal Presidio logging
        for name in ["presidio_analyzer", "presidio_anonymizer",
                      "presidio_analyzer.recognizer_registry"]:
            l = logging.getLogger(name)
            l.setLevel(logging.CRITICAL)
            l.propagate = False
        
        logging.info(
            f"[FinGuardPIIEngine] Initialized with {len(self._active_entities)} entities "
            f"({len(registry.recognizers)} recognizers active)."
        )

    def analyze(self, text: str) -> list:
        """Returns a list of `RecognizerResult` from Presidio."""
        return self._analyzer.analyze(
            text=text,
            entities=self._active_entities,
            language="en"
        )

    def scan(self, text: str) -> tuple[str, bool, float]:
        """Scanner-compatible interface: returns (sanitized_text, is_safe, risk_score)."""
        results = self.analyze(text)
        if not results:
            return text, True, 0.0
        
        anonymized = self._anonymizer.anonymize(text=text, analyzer_results=results)
        # Risk score is proportional to the max confidence of the highest-risk entity
        risk_score = max(r.score for r in results) if results else 0.0
        return anonymized.text, False, risk_score

    def redact(self, text: str) -> str:
        """Returns the text with all detected PII replaced by placeholders."""
        out, _, _ = self.scan(text)
        return out


def get_pii_engine(
    locale_packs: list[str] | None = None,
    extra_entities: list[str] | None = None,
    exclude_entities: list[str] | None = None,
) -> FinGuardPIIEngine:
    """Returns a cached singleton engine for a given configuration."""
    # Create a hashable cache key from the configuration
    key = str(sorted(locale_packs or [])) + str(sorted(extra_entities or [])) + str(sorted(exclude_entities or []))
    if key not in _ENGINE_CACHE:
        _ENGINE_CACHE[key] = FinGuardPIIEngine(locale_packs, extra_entities, exclude_entities)
    return _ENGINE_CACHE[key]
