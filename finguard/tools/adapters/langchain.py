import asyncio
from copy import copy
from typing import List, Any
from finguard.exceptions import ToolCallViolation

def wrap_langchain_tools(guard: Any, tools: List[Any], session_id: str = None) -> List[Any]:
    """
    Wraps a list of LangChain BaseTools.
    Dynamically overrides the `_run` and `_arun` methods to enforce FinGuard policies.
    """
    wrapped_tools = []
    
    for tool in tools:
        # Create a shallow copy of the tool so we don't mutate the global instance
        safe_tool = copy(tool)
        
        # Save original execution methods
        original_run = getattr(safe_tool, "_run", None)
        original_arun = getattr(safe_tool, "_arun", None)
        tool_name = safe_tool.name
        
        # Override async run
        if original_arun:
            async def secure_arun(*args, **kwargs):
                try:
                    # Enforce FinGuard Permissions
                    await guard.guard_tool_call(
                        tool_name=tool_name, 
                        arguments=kwargs or {}, 
                        session_id=session_id
                    )
                    return await original_arun(*args, **kwargs)
                except ToolCallViolation as e:
                    # Return a friendly string so the LangChain React agent 
                    # can self-correct instead of crashing the process!
                    return f"Action Failed: Blocked by FinGuard security policy. Reason: {e.trace.output_scanners[0].violations[0]['reason']}"
            
            # Rebind
            safe_tool._arun = secure_arun
            
        # Override sync run
        if original_run:
            def secure_run(*args, **kwargs):
                try:
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                    loop.run_until_complete(
                        guard.guard_tool_call(
                            tool_name=tool_name, 
                            arguments=kwargs or {}, 
                            session_id=session_id
                        )
                    )
                    return original_run(*args, **kwargs)
                except ToolCallViolation as e:
                    return f"Action Failed: Blocked by FinGuard security policy. Reason: {e.trace.output_scanners[0].violations[0]['reason']}"
            
            # Rebind
            safe_tool._run = secure_run
            
        wrapped_tools.append(safe_tool)
        
    return wrapped_tools
