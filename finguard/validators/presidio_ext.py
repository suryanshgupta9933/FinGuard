from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern

def init_presidio_analyzer() -> AnalyzerEngine:
    analyzer = AnalyzerEngine()
    
    pan_recognizer = PatternRecognizer(
        supported_entity="IN_PAN",
        patterns=[Pattern("PAN", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", 0.9)],
        context=["pan", "permanent account", "income tax"]
    )
    
    aadhaar_recognizer = PatternRecognizer(
        supported_entity="IN_AADHAAR",
        patterns=[Pattern("Aadhaar", r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b", 0.85)],
        context=["aadhaar", "uid", "unique identification"]
    )
    
    demat_recognizer = PatternRecognizer(
        supported_entity="IN_DEMAT",
        patterns=[Pattern("Demat", r"\b1[23]\d{14}\b", 0.8)],
        context=["demat", "depository", "dp id"]
    )
    
    # Register custom Indian PII recognizers
    for rec in [pan_recognizer, aadhaar_recognizer, demat_recognizer]:
        analyzer.registry.add_recognizer(rec)
        
    return analyzer
