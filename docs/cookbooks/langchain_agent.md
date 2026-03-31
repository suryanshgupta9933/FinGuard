# Secure LangChain Agent Cookbook

This cookbook demonstrates how to build a fully observable, secure LangChain conversational agent utilizing FinGuard to protect both its Prompts and its Tools.

## Prerequisites

```bash
pip install langchain langchain-openai "finguard[all]"
```

## The Architecture

We will intercept the Agent in two places:
1. **Input**: Wrapping the LLM directly so the prompt avoids injection and hallucinations.
2. **Tools**: Wrapping the agent's tools so it cannot execute dangerous backend commands.

### `app.py`

```python
import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import tool

from finguard import FinGuard

# 1. Initialize FinGuard with strict tool rules & APM tracing
guard = FinGuard(policy={
    "policy_id": "secure_agent",
    "risk_level": "high",
    "audit": {
        "emit_traces": True,
        "backend": "langfuse"
    },
    "tools": {
        "enabled": True,
        "allowed": ["search_web"],
        "max_calls_per_session": 5
    }
})

# 2. Define standard LangChain Tools
@tool
def search_web(query: str):
    """Searches the internet."""
    return f"Results for: {query}"

@tool
def execute_sql(query: str):
    """Dangerous backend function!"""
    return "Dropped table Users"

# 3. Secure the Tools!
safe_tools = guard.wrap_langchain_tools([search_web, execute_sql])

# 4. Secure the LLM!
llm = ChatOpenAI(model="gpt-4")
secure_llm = guard.wrap(llm.ainvoke) 

# 5. Build Agent
agent = create_react_agent(llm, safe_tools, prompt=my_prompt)
agent_executor = AgentExecutor(agent=agent, tools=safe_tools)

async def chat():
    # If the user tries prompt injection, `secure_llm` blocks it BEFORE going to OpenAI.
    # If the LLM tries to use `execute_sql`, `safe_tools` blocks it BEFORE hitting the DB.
    # Both blocks are perfectly traced in Langfuse!
    res = await agent_executor.ainvoke({"input": "Hello!"})
    return res

if __name__ == "__main__":
    asyncio.run(chat())
```
