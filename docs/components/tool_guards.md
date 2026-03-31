# Agentic Tool Guards

Most LLM firewalls focus purely on Prompt Injection. But in the enterprise, **unauthorized agent actions** (executing arbitrary SQL, emailing clients, deleting databases) are the #1 highest risk.

A prompt injection attack is only dangerous if the *agent has dangerous tools*. 
FinGuard acts as a zero-trust firewall *between* your Agent Orchestrator and your backend tools.

## The Problem

```python
# Unsafe! If the LLM is tricked by a bad document, it can call whatever it wants!
agent = create_react_agent(llm, tools=[ReadDB(), WriteDB(), DropDB()])
```

## The FinGuard Solution

You define declarative rules natively in your `policy.yaml`:

```yaml
tools:
  enabled: true
  allowed: ["read_db", "search_web"]
  blocked: ["drop_database", "write_db"]
  max_calls_per_session: 10
```

And then "wrap" your tools before handing them to the agent!

=== "LangChain / LlamaIndex"

    ```python
    from finguard import FinGuard

    guard = FinGuard(policy="high_security")

    raw_tools = [ReadDBTool(), WriteDBTool()]

    # 1 Line of Code completely isolates your infrastructure.
    # If the LLM tries to use WriteDB, FinGuard intercepts it!
    secure_tools = guard.wrap_langchain_tools(raw_tools)

    agent = create_react_agent(llm, tools=secure_tools)
    ```

=== "Vanilla Python"

    ```python
    from finguard import FinGuard
    from finguard.tools.adapters.vanilla import wrap_tool

    guard = FinGuard(policy="high_security")

    # Native Python execution context is perfectly intercepted.
    @wrap_tool(guard, tool_name="fetch_prices")
    async def fetch_prices(ticker: str):
        return get_price(ticker)
    ```

## Agentic Self-Correction via Typed Exceptions

When a traditional API blocks a tool, it throws a generic 500 server error and crashes the entire application loop.

When **FinGuard** blocks a tool, it raises a structured `ToolCallViolation`. Our `wrap_langchain_tools` adapter natively catches this exception and returns it *as a string* to the LLM agent:

> `"Action Failed: Blocked by FinGuard security policy. Reason: Tool 'drop_db' is explicitly blocked."`

The Agent Orchestrator reads this string in its history array, realizes its mistake, and can seamlessly attempt a safer alternative action without ruining the user's session!

## Session Tracker (Rate Limiting)

Agents commonly suffer from "hallucination loops", where they continuously call the same failing web search or database API thousands of times a minute.

By setting `max_calls_per_session: 10`, FinGuard's `SessionTracker` monitors the agent's context window. If the agent exceeds 10 tool invocations, FinGuard severs the pipeline, preventing runaway loops from destroying your cloud backend API budgets.
