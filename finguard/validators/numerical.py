import re

class NumericalClaimValidator:
    """
    Detects numerical figures in LLM output and warns if there is 
    potential hallucination where strict grounding is required.
    """
    def __init__(self, tolerance: float = 0.0):
        self.tolerance = tolerance

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        # Minimal naive numerical claim verification
        # Extract all numbers from output
        # If the output asserts quantitative facts not in the prompt, surface it
        
        prompt_numbers = set(re.findall(r'\b\d+(?:\.\d+)?(?:%|M|K|B)?\b', prompt, re.IGNORECASE))
        if not prompt_numbers:
            return output, True, 0.0

        output_numbers = set(re.findall(r'\b\d+(?:\.\d+)?(?:%|M|K|B)?\b', output, re.IGNORECASE))
        
        # Numbers in output not present in prompt
        ungrounded = output_numbers.difference(prompt_numbers)
        
        if ungrounded:
            # We flag this with a risk but don't strictly block in all scenarios
            # Risk is proportional to the number of ungrounded metrics.
            risk_score = min(1.0, len(ungrounded) * 0.2)
            return output, False, risk_score
            
        return output, True, 0.0
