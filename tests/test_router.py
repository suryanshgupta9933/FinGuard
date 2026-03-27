import pytest
from finguard.router import get_input_scanners, get_output_scanners
from finguard.config import PolicyConfig

def test_router_scanners():
    """Test that the router loads the correct scanners for a policy."""
    policy = PolicyConfig.load("wealth_mgmt_assistant_v1")
    
    # Check input scanners
    input_scanners = get_input_scanners("high", policy)
    scanner_names = [s.__class__.__name__ for s in input_scanners]
    assert "PromptInjection" in scanner_names
    assert "BanTopics" in scanner_names
    
    # Check output scanners
    output_scanners = get_output_scanners("high", policy)
    o_scanner_names = [s.__class__.__name__ for s in output_scanners]
    assert "NumericalClaimValidator" in o_scanner_names
    assert "CompliancePhraseDetector" in o_scanner_names
    assert "RegulatoryContextTagger" in o_scanner_names
