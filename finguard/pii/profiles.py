"""
FinGuard PII Profiles
Defines the entity sets for the mandatory finance base and optional locale packs.
"""

# --- Mandatory Finance Base ---
# Always loaded. Core financial + personal identifiers relevant to all geographies.
FINANCE_BASE_ENTITIES = [
    # Universal financial
    "CREDIT_CARD",       # Presidio native (Luhn checksum)
    "IBAN_CODE",         # Presidio native (International bank accounts)
    # Universal personal
    "EMAIL_ADDRESS",     # Presidio native
    "PHONE_NUMBER",      # Presidio native
    # Indian financial (default market, required for SEBI/RBI compliance)
    "IN_PAN",            # Presidio native (Pattern + context)
    "IN_AADHAAR",        # Presidio native (Pattern + Verhoeff checksum)
    "IN_IFSC",           # Custom (NEFT/RTGS bank routing code)
    "IN_VPA",            # Custom (UPI virtual payment address)
    "IN_DEMAT",          # Custom (NSDL/CDSL depository account)
    "IN_BANK_ACCOUNT",   # Custom (Generic bank account numbers)
]

# --- Optional Locale Packs ---
# Enabled via policy: pii.locale_packs: ["IN_EXTENDED", "US"]
LOCALE_PACKS = {
    # Extended Indian identifiers (less common, adds latency)
    "IN_EXTENDED": [
        "IN_VOTER",
        "IN_PASSPORT",
        "IN_VEHICLE_REGISTRATION",
    ],
    # US identifiers
    "US": [
        "US_SSN",
        "US_ITIN",
        "US_DRIVER_LICENSE",
    ],
    # UK identifiers
    "UK": [
        "UK_NHS",
        "UK_NINO",
    ],
    # Generic global extras (adds some overhead via NER)
    "GLOBAL": [
        "IP_ADDRESS",
        "LOCATION",
        "DATE_TIME",
        "URL",
    ],
}
