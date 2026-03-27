class RegulatoryContextTagger:
    """
    Tags the conversation with relevant frameworks (e.g. PMLA, DPDP, SEBI).
    Could be used to route to specific policies or just for audit.
    """
    KEYWORDS_MAP = {
        "PMLA": ["money laundering", "kyc", "aml", "suspicious transaction"],
        "DPDP": ["personal data", "consent", "privacy", "data protection"],
        "SEBI": ["stock", "mutual fund", "trading", "investment", "portfolio"],
        "RBI": ["loan", "repo", "interest rate", "banking", "credit card"]
    }
    
    def tag(self, text: str) -> list[str]:
        tags = []
        text_lower = text.lower()
        for tag, keywords in self.KEYWORDS_MAP.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        return tags

    def scan(self, prompt: str, output: str) -> tuple[str, bool, float]:
        # This scanner acts as an observer/tagger, always returns True for safety.
        # But we could attach metadata to the request if we hook it into the pipeline state.
        tags = self.tag(prompt + " " + output)
        if tags:
            # We use violations array as a side-channel for tagging in this simplistic model,
            # though architecturally it might be better elsewhere.
            # Returning True means it's safe.
            return output, True, 0.0
        return output, True, 0.0
