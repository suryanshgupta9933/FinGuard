"""
FinGuard — Native Presidio PII Engine Test Suite
Tests all changes in the new finguard.pii module.

Run: uv run pytest tests/test_pii_engine.py -v
"""
import pytest
from finguard.pii.engine import FinGuardPIIEngine, get_pii_engine
from finguard.pii.profiles import FINANCE_BASE_ENTITIES, LOCALE_PACKS


# ==============================================================================
# 1. Finance Base Validation
# ==============================================================================

class TestFinanceBase:
    """All entities in FINANCE_BASE_ENTITIES must produce a working engine."""

    def test_finance_base_entities_defined(self):
        assert len(FINANCE_BASE_ENTITIES) > 0
        assert "CREDIT_CARD" in FINANCE_BASE_ENTITIES
        assert "IBAN_CODE" in FINANCE_BASE_ENTITIES
        assert "IN_PAN" in FINANCE_BASE_ENTITIES
        assert "IN_AADHAAR" in FINANCE_BASE_ENTITIES
        assert "IN_IFSC" in FINANCE_BASE_ENTITIES
        assert "IN_VPA" in FINANCE_BASE_ENTITIES

    def test_engine_initializes_with_finance_base(self):
        engine = FinGuardPIIEngine()
        assert engine is not None
        assert len(engine._active_entities) >= len(FINANCE_BASE_ENTITIES) - 2


# ==============================================================================
# 2. Native Presidio Entities
# ==============================================================================

class TestNativePresidioEntities:

    @pytest.fixture(scope="class")
    def engine(self):
        return FinGuardPIIEngine()

    def test_credit_card_detected(self, engine):
        text = "My card number is 4111-1111-1111-1111"
        _, is_safe, score = engine.scan(text)
        assert not is_safe, "Credit card should be detected"
        assert score > 0.5

    def test_email_detected(self, engine):
        text = "Please contact me at test.user@example.com for details"
        _, is_safe, score = engine.scan(text)
        assert not is_safe, "Email address should be detected"

    def test_phone_detected(self, engine):
        text = "Call me on +91 98765 43210"
        _, is_safe, score = engine.scan(text)
        assert not is_safe, "Phone number should be detected"

    def test_in_pan_detected(self, engine):
        text = "My PAN card number is ABCDE1234F"
        _, is_safe, score = engine.scan(text)
        assert not is_safe, "IN_PAN should be detected"

    def test_in_aadhaar_detected(self, engine):
        text = "My Aadhaar is 5544 5678 9101"
        _, is_safe, score = engine.scan(text)
        assert not is_safe, "IN_AADHAAR should be detected"

    def test_clean_text_passes(self, engine):
        text = "What is my account balance for this month?"
        _, is_safe, score = engine.scan(text)
        assert is_safe, "Clean text should pass"
        assert score == 0.0


# ==============================================================================
# 3. Custom Financial Recognizers (IN_IFSC, IN_VPA, IN_DEMAT, IN_BANK_ACCOUNT)
# ==============================================================================

class TestCustomFinancialRecognizers:

    @pytest.fixture(scope="class")
    def engine(self):
        return FinGuardPIIEngine()

    def test_ifsc_detected(self, engine):
        text = "Transfer via IFSC code SBIN0001234"
        _, is_safe, _ = engine.scan(text)
        assert not is_safe, "IN_IFSC should be detected"

    def test_ifsc_redacted(self, engine):
        text = "My bank IFSC is HDFC0001234"
        redacted, _, _ = engine.scan(text)
        assert "HDFC0001234" not in redacted, "IFSC should be redacted"

    def test_vpa_detected(self, engine):
        text = "Please send to my UPI ID user@okaxis"
        _, is_safe, _ = engine.scan(text)
        assert not is_safe, "IN_VPA should be detected"

    def test_demat_detected_with_context(self, engine):
        text = "My NSDL demat account number is 1234567890123456"
        _, is_safe, _ = engine.scan(text)
        assert not is_safe, "IN_DEMAT with context should be detected"

    def test_bank_account_detected_with_context(self, engine):
        text = "My bank account number is 123456789012"
        _, is_safe, _ = engine.scan(text)
        assert not is_safe, "IN_BANK_ACCOUNT with context should be detected"


# ==============================================================================
# 4. Redaction Quality
# ==============================================================================

class TestRedactionQuality:

    @pytest.fixture(scope="class")
    def engine(self):
        return FinGuardPIIEngine()

    def test_pan_is_redacted(self, engine):
        text = "PAN: ABCDE1234F"
        redacted = engine.redact(text)
        assert "ABCDE1234F" not in redacted

    def test_ifsc_is_redacted(self, engine):
        text = "IFSC: SBIN0001234"
        redacted = engine.redact(text)
        assert "SBIN0001234" not in redacted

    def test_redaction_preserves_non_pii(self, engine):
        text = "Hello, my email is john@example.com. The weather is nice today."
        redacted = engine.redact(text)
        assert "john@example.com" not in redacted
        assert "weather is nice today" in redacted


# ==============================================================================
# 5. Singleton Cache
# ==============================================================================

class TestSingletonCache:

    def test_same_config_returns_same_instance(self):
        engine1 = get_pii_engine()
        engine2 = get_pii_engine()
        assert engine1 is engine2, "Should return the same cached instance"

    def test_different_locales_return_different_instances(self):
        engine_base = get_pii_engine()
        engine_us = get_pii_engine(locale_packs=["US"])
        assert engine_base is not engine_us, "Different configs should be different instances"

    def test_us_locale_includes_ssn(self):
        engine = get_pii_engine(locale_packs=["US"])
        assert "US_SSN" in engine._active_entities


# ==============================================================================
# 6. Locale Pack Configuration
# ==============================================================================

class TestLocalePackConfiguration:

    def test_all_locale_packs_defined(self):
        assert "IN_EXTENDED" in LOCALE_PACKS
        assert "US" in LOCALE_PACKS
        assert "UK" in LOCALE_PACKS
        assert "GLOBAL" in LOCALE_PACKS

    def test_in_extended_adds_voter(self):
        engine = get_pii_engine(locale_packs=["IN_EXTENDED"])
        assert "IN_VOTER" in engine._active_entities

    def test_exclude_entities_works(self):
        engine = get_pii_engine(exclude_entities=["CREDIT_CARD"])
        assert "CREDIT_CARD" not in engine._active_entities

    def test_extra_entities_works(self):
        engine = get_pii_engine(extra_entities=["IP_ADDRESS"])
        assert "IP_ADDRESS" in engine._active_entities
