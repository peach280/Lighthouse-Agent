import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
import tools
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Siemens Lighthouse Architect API")



class AuditRequest(BaseModel):
    target: str = Field(
        description="URL (http://localhost:3000) or absolute path to an HTML file"
    )
    categories: List[Literal["performance", "accessibility", "seo", "best-practices"]] = Field(
        default=["performance", "accessibility", "seo", "best-practices"],
        description="Lighthouse categories to audit",
    )





# =============================================================================
# Endpoints — fastapi-mcp auto-exposes these as MCP tools via operation_id
# =============================================================================

@app.post(
    "/analyze",
    operation_id="analyze_lighthouse",
    summary="Run a Lighthouse audit on a URL or HTML file",
    tags=["lighthouse"],
)
async def analyze_lighthouse(request: AuditRequest):
    """
    Run a Lighthouse audit on the specified target and return a detailed
    FAIL/WARN summary across performance, accessibility, SEO, and best-practices.
    Validates results against Siemens Healthineers UI standards (CLS, LCP, A11y).
    """
    try:
        print(f"Received audit request: target={request.target}, categories={request.categories}")
        summary = tools.analyze_lighthouse(request.target, request.categories)
        return {
            "summary": summary,
            "next_step": "Pass any failing audit_id + snippet to /fix to get a surgical code fix."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@app.get(
    "/meta",
    operation_id="get_meta",
    summary="Get metadata about this MCP server",
    tags=["meta"],
)
async def get_meta():
    return {
        "name": "Siemens Lighthouse Architect",
        "description": "Agentic Lighthouse auditor for Siemens Healthineers UI",
        "version": "1.0.0",
        "mcp_tools": ["analyze_lighthouse"],
    }


# =============================================================================
# MCP Server — auto-discovers all endpoints above as MCP tools
# =============================================================================

mcp = FastApiMCP(
    app,
    name="Lighthouse Architect",
    description="Lighthouse audit + fix skill for Siemens Healthineers UI agents",
    include_tags=["lighthouse"],          # only expose audit tools, not /meta
)

mcp.mount_http()



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)