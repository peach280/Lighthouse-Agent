import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import tools  # Your Agentic tools.py

app = FastAPI(title="Siemens Lighthouse Architect API")

class AuditRequest(BaseModel):
    target: str # Can be file path or localhost URL
    categories: Optional[List[str]] = None

class FixRequest(BaseModel):
    audit_id: str
    code_snippet: str
    context: Optional[str] = "Siemens Healthineers UI, React/JSX"

@app.post("/analyze")
async def analyze(request: AuditRequest):
    try:
        # The tool now handles URL vs File internally
        summary = tools.analyze_lighthouse(request.target, request.categories)
        return {
            "summary": summary,
            "next_step": "You can now pass any failing snippet to the /fix endpoint."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/meta")
async def get_meta():
    return {
        "name": "Siemens Lighthouse Architect",
        "description": "Agentic Lighthouse auditor for Siemens Healthineers UI",
        "version": "1.0.0",
        "capabilities": ["analyze", "fix"]
    }

@app.post("/fix")
async def fix(request: FixRequest):
    try:
        # Use the Agentic Groq-powered logic
        fix_result = tools.suggest_fix(
            audit_id=request.audit_id,
            code_snippet=request.code_snippet,
            context=request.context
        )
        return fix_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Run on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)