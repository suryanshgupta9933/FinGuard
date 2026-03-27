import re

class CompliancePhraseDetector:
    """
    Detects SEBI/RBI compliance violations in LLM output.
    
    Two-stage check:
    1. Hard block on legally prohibited phrases (guaranteed returns, risk-free)
    2. Soft check: if the LLM OUTPUT reads like financial advice, enforce disclaimers
    """
    VIOLATING_PHRASES = [
        r"guarantee\w*\s+returns?",
        r"risk-?free",
        r"surety\s+of\s+profit",
        r"100%\s+safe",
        r"assured\s+returns?",
    ]

    # Phrases that indicate the LLM is actively giving investment recommendations 
    ADVICE_OUTPUT_SIGNALS = [
        r"\brecommend\b", r"\bshould (buy|invest|purchase)\b", r"\badvise\b",
        r"\bbest (stocks?|funds?|options?)\b", r"\bguarantee\b", r"\bfor (high|maximum) returns\b",
    ]

    def __init__(self, disclaimers: list[str] = None):
        self.disclaimers = disclaimers or []
        self.compiled_rules = [re.compile(p, re.IGNORECASE) for p in self.VIOLATING_PHRASES]
        self.compiled_advice = [re.compile(p, re.IGNORECASE) for p in self.ADVICE_OUTPUT_SIGNALS]

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        # 1. Hard block: explicit prohibited phrases in output
        for rule in self.compiled_rules:
            if rule.search(output):
                return output, False, 1.0

        # 2. Disclaimer check: only enforce when the OUTPUT itself looks like advice
        # This correctly passes informational queries ("what is the risk profile of X")
        # and only blocks actual LLM recommendations ("I recommend buying X for high returns")
        output_looks_like_advice = any(sig.search(output) for sig in self.compiled_advice)

        if output_looks_like_advice:
            for disc in self.disclaimers:
                if disc.lower() not in output.lower():
                    return output, False, 0.5

        return output, True, 0.0
