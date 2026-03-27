"""
FinGuard Custom PII Recognizers
Fills the gaps in Presidio's default recognizer set for Indian financial identifiers.
"""
from presidio_analyzer import Pattern, PatternRecognizer


def build_custom_recognizers() -> list:
    """Returns a list of PatternRecognizer objects for financial entities
    not covered by Presidio's default recognizer set."""
    return [
        # IFSC Code — Indian banking routing code for NEFT/RTGS
        PatternRecognizer(
            supported_entity="IN_IFSC",
            patterns=[Pattern("IFSC", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", 0.85)],
            context=["ifsc", "rtgs", "neft", "bank", "branch", "routing"],
        ),
        # UPI Virtual Payment Address — Digital payment handle
        PatternRecognizer(
            supported_entity="IN_VPA",
            patterns=[Pattern("UPI_VPA", r"\b[\w.\-]{3,}@(okaxis|oksbi|okicici|okhdfc|ybl|axl|ibl|upi)\b", 0.9)],
            context=["upi", "vpa", "gpay", "phonepe", "bhim", "paytm", "pay"],
        ),
        # Demat Account — NSDL/CDSL securities account (16-digit starting with 1)
        PatternRecognizer(
            supported_entity="IN_DEMAT",
            patterns=[Pattern("DEMAT", r"\b1[0-9]{15}\b", 0.75)],
            context=["demat", "nsdl", "cdsl", "depository", "securities", "holdings"],
        ),
        # Bank Account Number — 9 to 18 digit account numbers
        # Low default score, boosted significantly by context
        PatternRecognizer(
            supported_entity="IN_BANK_ACCOUNT",
            patterns=[Pattern("BANK_ACCT", r"\b[0-9]{9,18}\b", 0.4)],
            context=["account", "savings", "current", "acc no", "a/c", "bank account"],
        ),
    ]
