import pytest
import asyncio
from finguard import FinGuard
from finguard.exceptions import ToolCallViolation
from finguard.tools.adapters.vanilla import wrap_tool

@pytest.fixture
def test_guard():
    # Setup a guard with a mix of allowed/blocked rules
    return FinGuard(policy={
        "policy_id": "test_tools",
        "risk_level": "medium",
        "tools": {
            "enabled": True,
            "blocked": ["drop_table", "execute_python", "write_db"],
            "max_calls_per_session": 3
        }
    })

@pytest.mark.asyncio
async def test_vanilla_adapter_allows_safe_tool(test_guard):
    @wrap_tool(test_guard, tool_name="read_db")
    async def my_tool(query: str):
        return f"Results for {query}"
        
    res = await my_tool(query="SELECT * FROM users", session_id="sess_1")
    assert res == "Results for SELECT * FROM users"
    
@pytest.mark.asyncio
async def test_vanilla_adapter_blocks_unsafe_tool(test_guard):
    @wrap_tool(test_guard, tool_name="drop_table")
    async def dangerous_tool():
        return "Dropped!"
        
    with pytest.raises(ToolCallViolation) as exc:
        await dangerous_tool(session_id="sess_2")
        
    assert "Blocked Tool Call" in str(exc.value)
    assert "explicitly blocked" in str(exc.value)
    
@pytest.mark.asyncio
async def test_vanilla_adapter_rate_limits(test_guard):
    @wrap_tool(test_guard, tool_name="read_db")
    async def looping_tool():
        return "Read success"
        
    # Max calls is 3. We should be able to call it 3 times successfully.
    await looping_tool(session_id="crazy_agent_loop")
    await looping_tool(session_id="crazy_agent_loop")
    await looping_tool(session_id="crazy_agent_loop")
    
    # 4th time should block!
    with pytest.raises(ToolCallViolation) as exc:
        await looping_tool(session_id="crazy_agent_loop")
        
    assert "Exceeded max_calls_per_session" in str(exc.value)
