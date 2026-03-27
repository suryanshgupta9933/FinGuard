import re
from typing import Tuple, List, Dict, Any

class IndianFinancialPII:
    """
    High-speed Regex-based detector for Indian financial identifiers.
    Avoids the ~170ms NER overhead for common standard formats.
    """
    PATTERNS = {
        "IN_PAN": r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
        "IN_AADHAAR": r"\b[1-9]{1}[0-9]{3}[\s-]?[0-9]{4}[\s-]?[0-9]{4}\b",
        "IN_IFSC": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "IN_VPA": r"\b[\w\.\-]+@[\w\-]+\.[\w\-]+\b",
    }

    def __init__(self, entities: List[str] = None):
        self.entities = entities or ["IN_PAN", "IN_AADHAAR", "IN_IFSC", "IN_VPA"]
        self.compiled = {k: re.compile(v) for k, v in self.PATTERNS.items() if k in self.entities}

    def scan(self, text: str) -> Tuple[str, bool, float]:
        violations = []
        sanitized_text = text
        
        for name, prog in self.compiled.items():
            matches = prog.findall(text)
            if matches:
                violations.append(name)
                for m in matches:
                    sanitized_text = sanitized_text.replace(m, f"[{name}]")

        if violations:
            return sanitized_text, False, 0.9 # High risk for financial PII
            
        return sanitized_text, True, 0.0

class PMLAScanner:
    """
    Prevention of Money Laundering Act (PMLA) heuristic scanner.
    Flags suspicious high-value transfer attempts or unusual transaction patterns.
    """
    TRANSFER_KEYWORDS = ["transfer", "send", "wire", "remit"]
    
    def __init__(self, threshold_amount: float = 50000.0):
        self.threshold_amount = threshold_amount

    def scan(self, text: str) -> Tuple[str, bool, float]:
        # Look for transfer keywords + large numbers with optional currency symbols
        text_lower = text.lower()
        if any(kw in text_lower for kw in self.TRANSFER_KEYWORDS):
            # Combined regex for digits, commas, and currency symbols
            numbers = re.findall(r"(?:₹|\$|GBP|EUR|INR)?\s?([\d,]+(?:\.\d+)?)", text)
            for num_str in numbers:
                try:
                    num = float(num_str.replace(",", ""))
                    if num >= self.threshold_amount:
                        return text, False, 1.0
                except ValueError:
                    continue
        
        return text, True, 0.0
