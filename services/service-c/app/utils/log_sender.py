import os
from typing import Optional

import httpx

ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://localhost:8000")


async def send_log(
    trace_id: str,
    service_name: str,
    status: str,
    error_type: Optional[str] = None,
    message: Optional[str] = None,
    duration_ms: Optional[float] = None,
) -> None:
    """Send a structured log entry to the admin service. Fire-and-forget."""
    payload = {
        "trace_id": trace_id,
        "service_name": service_name,
        "status": status,
        "error_type": error_type,
        "message": message,
        "duration_ms": duration_ms,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{ADMIN_SERVICE_URL}/logs/", json=payload)
    except Exception:
        pass