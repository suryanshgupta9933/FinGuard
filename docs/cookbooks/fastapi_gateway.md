# FastAPI API Proxy Cookbook

Instead of wrapping application code, you can run FinGuard as a standalone API Gateway! This intercepts HTTP traffic before it reaches your backend LLMs.

## Prerequisites
```bash
pip install fastapi uvicorn "finguard[all]"
```

## The Code

Save the following as `proxy.py`:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from finguard import FinGuard
from finguard.schema import GuardRequest
from finguard.exceptions import FinGuardViolation

guard = FinGuard(policy="retail_banking")
app = FastAPI(title="FinGuard LLM Proxy")

class ChatRequest(BaseModel):
    message: str
    session_id: str
    metadata: Dict[str, Any] = {}

# Mock LLM API
async def raw_llm_backend(prompt: str) -> str:
    return f"Response to: {prompt}"

@app.post("/v1/chat")
async def secure_chat(req: ChatRequest):
    
    # 1. Bind the raw string to a GuardRequest for pipeline entry
    guard_req = GuardRequest(
        prompt=req.message,
        metadata={"session_id": req.session_id, **req.metadata}
    )
    
    try:
        # 2. FinGuard executes its intercept
        safe_response = await guard(guard_req, raw_llm_backend)
        return {"response": safe_response.output, "trace_id": safe_response.trace.trace_id}
        
    except FinGuardViolation as e:
        # 3. Handle blocks deterministically
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "FinGuard Blocked the Prompt",
                "reason": e.trace.input_scanners[0].violations,
                "trace_id": e.trace.trace_id
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Running it

```bash
uv run python proxy.py
```

Because FinGuard evaluates rules strictly via the loaded `retail_banking` policy, your backend LLMs can remain completely isolated inside a private subnet. The FastAPI proxy absorbs the injection attacks natively!
