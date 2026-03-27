import re

class CompliancePhraseDetector:
    """
    Detects SEBI/RBI violating phrases like 'guaranteed returns' or 'risk-free'.
    """
    VIOLATING_PHRASES = [
        r"guarantee\w*\s+returns?", 
        r"risk-?free", 
        r"surety\s+of\s+profit",
        r"100%\s+safe"
    ]
    
    def __init__(self, disclaimers: list[str] = None):
        self.disclaimers = disclaimers or []
        self.compiled_rules = [re.compile(p, re.IGNORECASE) for p in self.VIOLATING_PHRASES]

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        violations = []
        for rule in self.compiled_rules:
            if rule.search(output):
                violations.append(rule.pattern)

        if violations:
            return output, False, 1.0
            
        # Check if required disclaimers are present (Naive check)
        for disc in self.disclaimers:
            if disc.lower() not in output.lower():
                # Missing disclaimer
                return output, False, 0.5
                
        return output, True, 0.0
