import logging
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

logger = logging.getLogger("mcp")

from app.models.database import get_db
from app.routers.infra import restart_service, scale_service, stop_service

router = APIRouter(prefix="/mcp", tags=["mcp"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

class MCPRequest(BaseModel):
    prompt: str

class MCPResponse(BaseModel):
    success: bool
    action: str
    service_name: str
    message: str

async def call_gemini(prompt: str) -> dict:
    """Use Gemini REST API to extract intent from natural language prompt."""
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY is not configured in .env")

    import asyncio, json

    models = ["gemini-2.0-flash", "gemini-flash-latest"]
    system_prompt = (
        "You are an AI DevOps router. Given the prompt, determine the action "
        "(restart, scale, stop), the target service (service-a, service-b, service-c), "
        "optionally replicas (int, default 2 for scale), and whether the user approves "
        "or rejects the action (approval_status: 'approved' or 'rejected'). "
        "Return strictly valid JSON with keys: action, service_name, replicas, approval_status.\n"
        f"Prompt: {prompt}"
    )
    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    headers = {"X-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}

    last_error = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(text)
            if response.status_code == 503:
                last_error = f"{model} returned 503 (attempt {attempt+1})"
                await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
                continue
            last_error = f"Gemini API error ({response.status_code}): {response.text[:200]}"
            break  # non-retryable error, try next model

    raise Exception(f"All Gemini models failed. Last error: {last_error}")

@router.post("/execute", response_model=MCPResponse)
async def execute_mcp_command(request: MCPRequest, db: Session = Depends(get_db)):
    """
    Exposes an MCP-like interface where a Gemini agent decides which 
    backend infra controller to invoke based on natural language.
    All actions invoked here are automatically captured in AuditLog 
    via the underlying infra routers.
    """
    logger.info(f"[MCP] Incoming request — prompt: {request.prompt}")
    try:
        if not GEMINI_API_KEY:
            # Fallback simple keyword matching if key is missing (for local testing without keys)
            action = "unknown"
            if "restart" in request.prompt.lower(): action = "restart"
            elif "scale" in request.prompt.lower(): action = "scale"
            elif "stop" in request.prompt.lower(): action = "stop"
            
            service_name = "service-a"
            if "service-b" in request.prompt.lower(): service_name = "service-b"
            if "service-c" in request.prompt.lower(): service_name = "service-c"
            
            approval_status = "rejected" if "reject" in request.prompt.lower() or "deny" in request.prompt.lower() else "approved"
            intent = {"action": action, "service_name": service_name, "replicas": 2, "approval_status": approval_status}
        else:
            intent = await call_gemini(request.prompt)

        action = intent.get("action", "").lower()
        service_name = intent.get("service_name", "").lower()
        replicas = intent.get("replicas", 2)
        approval_status = intent.get("approval_status", "approved").lower()

        from app.models.tables import AuditLog
        prompt_text = request.prompt

        if approval_status == "rejected":
            db.add(AuditLog(
                action=f"{action}:{service_name}",
                approved_by="mcp_agent",
                details=f"status=rejected | prompt={prompt_text} | Action was rejected by user, operation aborted."
            ))
            db.commit()
            return {"success": True, "action": action, "service_name": service_name, "message": "Action was rejected by user. Logged to audit."}

        # Approved — execute and log with prompt
        if action == "restart":
            result = restart_service(service_name=service_name, incident_id=None, db=db)
        elif action == "scale":
            result = scale_service(service_name=service_name, replicas=replicas, incident_id=None, db=db)
        elif action == "stop":
            result = stop_service(service_name=service_name, db=db)
        else:
            db.add(AuditLog(
                action=f"unknown:{service_name}",
                approved_by="mcp_agent",
                details=f"status=unsupported | prompt={prompt_text} | Could not map to a known action."
            ))
            db.commit()
            return {"success": False, "action": str(action), "service_name": str(service_name), "message": "Unknown or unsupported action derived from prompt"}

        # Overwrite the auto-created audit entry with the prompt context
        db.add(AuditLog(
            action=f"mcp:{action}:{service_name}",
            approved_by="mcp_agent",
            details=f"status=approved | prompt={prompt_text} | result={result['message']}"
        ))
        db.commit()
        return {"success": result["success"], "action": action, "service_name": service_name, "message": result["message"]}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
