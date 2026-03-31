import functools
import inspect
import asyncio
from typing import Any, Callable

def wrap_tool(guard: Any, tool_name: str = None):
    """
    Vanilla Python decorator to wrap any arbitrary tool function.
    Usage:
        @wrap_tool(guard, "execute_sql")
        async def my_db_function(query: str, session_id: str): ...
    """
    def decorator(func: Callable):
        name = tool_name or func.__name__
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract session_id for rate limiting, don't pass to underlying func
                session_id = kwargs.pop("session_id", None)
                
                # Check with FinGuard first explicitly
                await guard.guard_tool_call(
                    tool_name=name, 
                    arguments=kwargs, 
                    session_id=session_id
                )
                
                # If guard_tool_call didn't raise FinGuardViolation, it's safe to run
                return await func(*args, **kwargs)
            return wrapper
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                session_id = kwargs.pop("session_id", None)
                
                # We need to run the async guard check in a sync context
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                loop.run_until_complete(
                    guard.guard_tool_call(
                        tool_name=name, 
                        arguments=kwargs, 
                        session_id=session_id
                    )
                )
                
                return func(*args, **kwargs)
            return wrapper
            
    return decorator
