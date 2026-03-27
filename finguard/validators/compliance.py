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
    
    # Keywords that suggest the model is giving actual investment advice
    ADVICE_KEYWORDS = ["invest", "return", "mutual fund", "stock", "portfolio", "yield", "profit"]

    def __init__(self, disclaimers: list[str] = None):
        self.disclaimers = disclaimers or []
        self.compiled_rules = [re.compile(p, re.IGNORECASE) for p in self.VIOLATING_PHRASES]

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        violations = []
        prompt_lower = prompt.lower()
        output_lower = output.lower()
        
        # 1. Check for explicit violations (Guaranteed returns, etc.) in output
        for rule in self.compiled_rules:
            if rule.search(output):
                violations.append(rule.pattern)

        if violations:
            return output, False, 1.0
            
        # 2. Heuristic: Only enforce disclaimers if the PROMPT actually relates to financial advice
        # This avoids blocking standard history/balance queries.
        is_advice_requested = any(key in prompt_lower for key in self.ADVICE_KEYWORDS)
        
        if is_advice_requested:
            for disc in self.disclaimers:
                if disc.lower() not in output_lower:
                    # Missing required disclaimer for detected advice intent
                    return output, False, 0.5
                
        return output, True, 0.0
