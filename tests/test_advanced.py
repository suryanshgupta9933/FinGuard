import pytest
import asyncio
from finguard import FinGuard

@pytest.mark.asyncio
async def test_output_pii_redaction():
    # Policy with output redaction enabled
    policy = {
        "policy_id": "test_redaction",
        "pii": {
            "enabled": True,
            "entities": ["EMAIL_ADDRESS", "PHONE_NUMBER"],
            "redact_output": True
        },
        "output": {
            "on_fail": "pass" # We want to see the redacted output, not a block
        }
    }
    
    guard = FinGuard(policy=policy)
    
    @guard.wrap
    async def mock_llm(p: str):
        # We need to return valid financial-sounding context if we want to avoid 
        # auto-disclaimer blocks if we used that scanner, but here we just test PII.
        return "You can contact me at test@example.com or call 123-456-7890."
    
    # Run
    result = await mock_llm("Give me contact info")
    
    # Check if redacted
    assert "test@example.com" not in result
    assert "123-456-7890" not in result
    # Presidio with Vault usually replaces with [EMAIL_ADDRESS] or similar
    assert "[EMAIL_ADDRESS]" in result or "[PHONE_NUMBER]" in result or "[REDACTED]" in result or "test" not in result

@pytest.mark.asyncio
async def test_pmla_blocking():
    # PMLA should block large amounts by default
    guard = FinGuard(policy={"policy_id": "test_pmla"})
    
    @guard.wrap
    async def mock_llm(p: str): return "OK"
    
    # Large amount
    with pytest.raises(ValueError, match="PMLAScanner"):
        await mock_llm("Transfer 75,000 to John")
        
    # Small amount (Should pass)
    res = await mock_llm("Transfer 10 to John")
    assert res == "OK"

@pytest.mark.asyncio
async def test_compliance_false_positive_history():
    # Transaction history should NOT be blocked even if it contains 'history'
    guard = FinGuard(policy="wealth_mgmt_assistant_v1")
    
    @guard.wrap
    async def mock_llm(p: str): return "Here is your history: [Data]"
    
    # Should PASS now
    res = await mock_llm("Show me my transaction history")
    assert "history" in res
    # Regex based fast path for Indian IDs
    policy = {
        "policy_id": "test_fast_pii",
        "pii": {"enabled": True, "entities": ["IN_PAN"]},
    }
    guard = FinGuard(policy=policy)
    
    @guard.wrap
    async def mock_llm(p: str): return "OK"
    
    # PAN Card (Should block because it violates PII in input)
    with pytest.raises(ValueError, match="IndianFinancialPII"):
        await mock_llm("My PAN is ABCDE1234F")
    # Use a dictionary instead of "default" string to avoid file loading issues in tests
    policy = {
        "policy_id": "test_latency",
        "injection": {"enabled": True}
    }
    guard = FinGuard(policy=policy)
    
    @guard.wrap
    async def mock_llm(p: str):
        return "Safe response"
        
    # We need to call the guard directly to get the GuardResult with latencies
    from finguard.schema import GuardRequest
    req = GuardRequest(prompt="Hello")
    
    async def llm_fn(p): return "Safe"
    
    res = await guard(req, llm_fn)
    
    assert res.component_latencies is not None
    assert len(res.component_latencies) > 0
    # Check for specific scanner keys
    assert any("Injection" in k for k in res.component_latencies.keys())
