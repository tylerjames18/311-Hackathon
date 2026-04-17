#!/usr/bin/env python3
"""
Boston Data Hub — Web API Backend
Author: Jude Ighomena | Janna AI Research Labs

Run:  python web_server.py
Then open: http://localhost:8000
"""

import os, json, asyncio, requests
from datetime import datetime
from typing import AsyncIterator

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse, HTMLResponse
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    print("❌  Run: pip install fastapi uvicorn anthropic requests")
    import sys; sys.exit(1)

import anthropic
from boston_agents import AGENT_REGISTRY, TOOLS, execute_tool, MAX_ITERATIONS

app = FastAPI(title="Boston Data Hub API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class QueryRequest(BaseModel):
    query:     str
    agent_key: str = "orchestrator"

@app.get("/agents")
def list_agents():
    return {k: {"name": v["name"], "emoji": v["emoji"], "description": v["description"]}
            for k, v in AGENT_REGISTRY.items()}

@app.post("/query")
async def query_agent(req: QueryRequest):
    if req.agent_key not in AGENT_REGISTRY:
        raise HTTPException(400, f"Unknown agent: {req.agent_key}")

    async def stream() -> AsyncIterator[str]:
        agent    = AGENT_REGISTRY[req.agent_key]
        client   = anthropic.Anthropic()
        messages = [{"role": "user", "content": req.query}]

        yield f"data: {json.dumps({'type': 'agent_start', 'agent': agent['name'], 'emoji': agent['emoji']})}\n\n"
        await asyncio.sleep(0)

        for iteration in range(MAX_ITERATIONS):
            resp = client.messages.create(
                model      = "claude-sonnet-4-5-20251001",
                max_tokens = 4096,
                system     = agent["system"],
                tools      = TOOLS,
                messages   = messages
            )

            if resp.stop_reason == "tool_use":
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        yield f"data: {json.dumps({'type': 'tool_call', 'tool': block.name, 'input': block.input})}\n\n"
                        await asyncio.sleep(0)
                        result = execute_tool(block.name, block.input)
                        yield f"data: {json.dumps({'type': 'tool_result', 'tool': block.name, 'chars': len(result)})}\n\n"
                        await asyncio.sleep(0)
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})
                messages.append({"role": "assistant", "content": resp.content})
                messages.append({"role": "user",      "content": tool_results})
            else:
                answer = "".join(b.text for b in resp.content if hasattr(b, "text"))
                yield f"data: {json.dumps({'type': 'answer', 'text': answer})}\n\n"
                yield "data: [DONE]\n\n"
                return

        yield f"data: {json.dumps({'type': 'error', 'text': 'Max iterations reached'})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(),
            "mcp_server": "https://data-mcp.boston.gov/mcp"}

if __name__ == "__main__":
    import uvicorn
    print("\n🏙️  Boston Data Hub Web Server")
    print("    API:  http://localhost:8000")
    print("    UI:   open index.html in your browser (or serve alongside)")
    print("    Docs: http://localhost:8000/docs\n")
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)
