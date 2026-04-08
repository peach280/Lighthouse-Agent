import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List,Literal
import tools
from fastapi_mcp import FastApiMCP

app = FastAPI(title="Siemens Lighthouse Architect API")

# Initialize MCP early so we can register tools
mcp = FastApiMCP(app, name="Lighthouse Architect")


class AuditRequest(BaseModel):
    target: str = Field(
        description="URL (http://localhost:3000) or absolute path to an HTML file"
    )
    categories: List[Literal["performance", "accessibility", "seo", "best-practices"]] = Field(
        default=["performance", "accessibility", "seo", "best-practices"],
        description="Lighthouse categories to audit",
    )

    model_config = {
        "json_schema_extra": {
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {                          # ← this is the exact fix
                        "type": "string",
                        "enum": ["performance", "accessibility", "seo", "best-practices"]
                    },
                    "default": ["performance", "accessibility", "seo", "best-practices"],
                    "description": "Lighthouse categories to audit"
                }
            }
        }
    }

class FixRequest(BaseModel):
    audit_id: str
    code_snippet: str
    context: Optional[str] = "Siemens Healthineers UI, React/JSX"


# =============================================================================
# MCP Tool Registration - These are discoverable by Copilot and other MCP clients
# =============================================================================

@mcp.tool("analyze_lighthouse")
def analyze_lighthouse_tool(
    target: str = Field(description="URL (http://localhost:3000) or absolute path to an HTML file"),
    categories: Optional[List[Literal["performance", "accessibility", "seo", "best-practices"]]] = Field(
        default=["performance", "accessibility", "seo", "best-practices"],
        description="Lighthouse categories to audit"
    )
) -> str:
    """
    Run a Lighthouse audit on the specified target and return a detailed analysis summary.

    Args:
        target: URL or file path to audit
        categories: List of Lighthouse categories to include in the audit

    Returns:
        Detailed audit summary with failing audits, scores, and actionable insights
    """
    try:
        return tools.analyze_lighthouse(target, categories)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lighthouse audit failed: {str(e)}")


@mcp.tool("suggest_fix")
def suggest_fix_tool(
    audit_id: str = Field(description="Lighthouse audit ID that failed (e.g., 'image-alt', 'color-contrast')"),
    code_snippet: str = Field(description="The problematic code snippet to fix"),
    context: Optional[str] = Field(
        default="Siemens Healthineers UI, React/JSX",
        description="Additional context about the codebase (framework, version, etc.)"
    )
) -> dict:
    """
    Get an AI-powered fix suggestion for a specific Lighthouse audit failure.

    Args:
        audit_id: The Lighthouse audit that failed
        code_snippet: The code that needs to be fixed
        context: Additional context to help generate better fixes

    Returns:
        Dictionary with before/after code, explanation, and any caveats
    """
    try:
        return tools.suggest_fix(audit_id, code_snippet, context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fix suggestion failed: {str(e)}")

@app.post("/analyze")
async def mcp_analyze_lighthouse(request: AuditRequest):
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
        "capabilities": ["analyze", "fix"],
        "mcp_tools": ["analyze_lighthouse", "suggest_fix"]
    }

@app.get("/tools")
async def list_tools():
    """List available MCP tools for debugging"""
    return {
        "tools": [
            {
                "name": "analyze_lighthouse",
                "description": "Run Lighthouse audit and get detailed analysis",
                "parameters": {
                    "target": "URL or file path to audit",
                    "categories": "Lighthouse categories to include (optional)"
                }
            },
            {
                "name": "suggest_fix",
                "description": "Get AI-powered fix for Lighthouse audit failures",
                "parameters": {
                    "audit_id": "Lighthouse audit ID that failed",
                    "code_snippet": "Code snippet to fix",
                    "context": "Additional context (optional)"
                }
            }
        ]
    }

@app.post("/fix")
async def mcp_suggest_fix(request: FixRequest):
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


# =============================================================================
# MCP Server Setup - Mount the MCP protocol handler
# =============================================================================

@app.get("/mcp")
async def mcp_handshake():
    """Health check endpoint for MCP server status"""
    return {"status": "ok", "message": "MCP Server is running"}

# Mount the MCP protocol handler - this enables tool discovery and execution
mcp.mount()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)