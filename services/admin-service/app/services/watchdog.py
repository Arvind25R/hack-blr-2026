import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.tables import Incident, Log
from app.services.qdrant_service import get_best_solution

logger = logging.getLogger("watchdog")

# ─── Configurable thresholds (via env vars) ──────────────────────
LATENCY_THRESHOLD_MS = float(os.getenv("LATENCY_THRESHOLD_MS", "3000"))
EXCEPTION_THRESHOLD = int(os.getenv("EXCEPTION_THRESHOLD", "3"))
POLL_INTERVAL_SECONDS = int(os.getenv("WATCHDOG_POLL_INTERVAL", "10"))
WINDOW_SECONDS = int(os.getenv("WATCHDOG_WINDOW_SECONDS", "60"))
VAPI_RETRY_SECONDS = int(os.getenv("VAPI_RETRY_SECONDS", "120"))  # re-call Vapi if still down after this
MIN_LOGS_FOR_DETECTION = 2

# ─── Service URLs for health checks ─────────────────────────────
SERVICE_URLS = {
    "service-a": os.getenv("SERVICE_A_URL", "http://localhost:8001"),
    "service-b": os.getenv("SERVICE_B_URL", "http://localhost:8002"),
    "service-c": os.getenv("SERVICE_C_URL", "http://localhost:8003"),
}

SERVICES = list(SERVICE_URLS.keys())

# Issue codes for Vapi calls
ISSUE_CODES = {
    "service_down": "SVC_DOWN_001",
    "high_latency": "SVC_LATENCY_002",
    "null_pointer": "APP_NPE_003",
}


def _get_recent_logs(db: Session, service_name: str, window_seconds: int) -> list[Log]:
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    return (
        db.query(Log)
        .filter(Log.service_name == service_name, Log.timestamp >= cutoff)
        .all()
    )


def _has_active_incident(db: Session, service_name: str, incident_type: Optional[str] = None) -> bool:
    """Check if there's already an unresolved incident for this service (optionally of a specific type)."""
    active_statuses = ["DETECTED", "ANALYZED", "USER_NOTIFIED", "APPROVED", "ACTION_TAKEN"]
    query = db.query(Incident).filter(
        Incident.service_name == service_name,
        Incident.status.in_(active_statuses),
    )
    if incident_type:
        query = query.filter(Incident.error_summary.contains(incident_type))
    return query.first() is not None


def _get_active_incident(db: Session, service_name: str, incident_type: str) -> Optional[Incident]:
    """Return the active incident for a service+type, or None."""
    active_statuses = ["DETECTED", "ANALYZED", "USER_NOTIFIED", "APPROVED", "ACTION_TAKEN"]
    return (
        db.query(Incident)
        .filter(
            Incident.service_name == service_name,
            Incident.status.in_(active_statuses),
            Incident.error_summary.contains(incident_type),
        )
        .order_by(desc(Incident.created_at))
        .first()
    )


def _should_retry_vapi(incident: Incident) -> bool:
    """Return True if enough time has passed since the last update to re-call Vapi."""
    last_touch = incident.updated_at or incident.created_at
    elapsed = (datetime.utcnow() - last_touch).total_seconds()
    return elapsed >= VAPI_RETRY_SECONDS


def _create_incident(
    db: Session,
    service_name: str,
    severity: str,
    error_summary: str,
    trace_id: Optional[str] = None,
) -> Incident:
    incident = Incident(
        trace_id=trace_id,
        service_name=service_name,
        severity=severity,
        status="DETECTED",
        error_summary=error_summary,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    logger.info(f"Incident #{incident.id} created for {service_name}: {error_summary}")

    # Query Qdrant for suggested solution
    try:
        solution = get_best_solution(error_summary)
        if solution:
            incident.suggested_solution = (
                f"[Action: {solution['action_type']}] "
                f"Root cause: {solution['root_cause']} "
                f"Fix: {solution['recommended_fix']}"
            )
            incident.status = "ANALYZED"
            db.commit()
            db.refresh(incident)
            logger.info(f"Incident #{incident.id} analyzed — action: {solution['action_type']}")
    except Exception as exc:
        logger.warning(f"Qdrant lookup failed for incident #{incident.id}: {exc}")

    return incident


async def _check_health(service_name: str) -> bool:
    """Ping the /health endpoint of a service. Returns True if healthy."""
    url = SERVICE_URLS.get(service_name)
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/health")
            return resp.status_code == 200
    except Exception:
        return False

async def _detect_service_down(db: Session, service_name: str) -> Optional[Incident]:
    """Check if a service is down by pinging its /health endpoint."""
    healthy = await _check_health(service_name)
    if not healthy:
        if _has_active_incident(db, service_name, ISSUE_CODES["service_down"]):
            return None
        summary = (
            f"[{ISSUE_CODES['service_down']}] Service {service_name} is DOWN — "
            f"health check at {SERVICE_URLS[service_name]}/health failed."
        )
        return _create_incident(db, service_name, severity="critical", error_summary=summary)
    return None


def _detect_high_latency(db: Session, service_name: str, logs: list[Log]) -> Optional[Incident]:
    """Detect logs where timetaken exceeds the configurable threshold."""
    high_latency_logs = [
        log for log in logs
        if log.duration_ms is not None and log.duration_ms >= LATENCY_THRESHOLD_MS
    ]
    if len(high_latency_logs) < MIN_LOGS_FOR_DETECTION:
        return None
    if _has_active_incident(db, service_name, ISSUE_CODES["high_latency"]):
        return None

    avg_duration = sum(l.duration_ms for l in high_latency_logs) / len(high_latency_logs)
    summary = (
        f"[{ISSUE_CODES['high_latency']}] High latency detected on {service_name}: "
        f"{len(high_latency_logs)} requests above {LATENCY_THRESHOLD_MS}ms threshold "
        f"(avg {avg_duration:.0f}ms) in last {WINDOW_SECONDS}s. Consider scaling up."
    )
    return _create_incident(
        db, service_name, severity="medium", error_summary=summary,
        trace_id=high_latency_logs[-1].trace_id,
    )


def _detect_null_pointer_exceptions(db: Session, service_name: str, logs: list[Log]) -> Optional[Incident]:
    """Detect NullPointerException / application errors above the configurable threshold."""
    npe_logs = [
        log for log in logs
        if log.error_type in ("NullPointerException", "null_pointer", "internal_error")
        and log.message and "nullpointer" in log.message.lower()
    ]
    # Also check for generic exception patterns in message
    npe_logs += [
        log for log in logs
        if log not in npe_logs
        and log.status == "ERROR"
        and log.message
        and any(kw in log.message.lower() for kw in ("nullpointerexception", "null pointer", "nonetype", "attributeerror"))
    ]

    if len(npe_logs) < EXCEPTION_THRESHOLD:
        return None
    if _has_active_incident(db, service_name, ISSUE_CODES["null_pointer"]):
        return None

    error_messages = set(log.message[:80] for log in npe_logs if log.message)
    summary = (
        f"[{ISSUE_CODES['null_pointer']}] Application errors detected on {service_name}: "
        f"{len(npe_logs)} NullPointerException/application errors in last {WINDOW_SECONDS}s. "
        f"Errors: {'; '.join(list(error_messages)[:3])}. "
        f"This is a genuine application bug — no infra action required."
    )
    return _create_incident(
        db, service_name, severity="high", error_summary=summary,
        trace_id=npe_logs[-1].trace_id,
    )


async def _trigger_vapi_for_incident(incident: Incident) -> None:
    """Auto-trigger Vapi call after incident is analyzed."""
    try:
        from app.services.vapi_service import trigger_voice_call
        result = await trigger_voice_call(
            incident_id=incident.id,
            service_name=incident.service_name,
            error_summary=incident.error_summary or "",
            suggested_solution=incident.suggested_solution or "",
        )
        logger.info(f"Vapi call result for incident #{incident.id}: {result.get('status', 'unknown')}")
        # Update status to USER_NOTIFIED
        db = SessionLocal()
        try:
            inc = db.query(Incident).filter(Incident.id == incident.id).first()
            if inc and inc.status == "ANALYZED":
                inc.status = "USER_NOTIFIED"
                inc.updated_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"Failed to trigger Vapi for incident #{incident.id}: {exc}")


def run_detection_cycle_sync(db: Session) -> list[Incident]:
    """Synchronous part of detection — log-based checks only."""
    new_incidents: list[Incident] = []

    for service_name in SERVICES:
        logs = _get_recent_logs(db, service_name, WINDOW_SECONDS)

        # Check high latency (scale up scenario)
        if not _has_active_incident(db, service_name, ISSUE_CODES["high_latency"]):
            incident = _detect_high_latency(db, service_name, logs)
            if incident:
                new_incidents.append(incident)

        # Check NullPointerExceptions (app error scenario)
        if not _has_active_incident(db, service_name, ISSUE_CODES["null_pointer"]):
            incident = _detect_null_pointer_exceptions(db, service_name, logs)
            if incident:
                new_incidents.append(incident)

    return new_incidents


async def run_detection_cycle() -> list[dict]:
    """Run one full detection cycle across all services. Returns new incident summaries."""
    db = SessionLocal()
    new_incidents: list[dict] = []
    incidents_for_vapi: list[Incident] = []

    try:
        # 1. Health-check based detection (service down → restart)
        for service_name in SERVICES:
            existing = _get_active_incident(db, service_name, ISSUE_CODES["service_down"])
            if existing:
                # Service already has an active incident — check if we should re-call Vapi
                healthy = await _check_health(service_name)
                if not healthy and _should_retry_vapi(existing):
                    logger.info(
                        f"Service {service_name} still DOWN after {VAPI_RETRY_SECONDS}s — re-triggering Vapi for incident #{existing.id}"
                    )
                    existing.updated_at = datetime.utcnow()
                    db.commit()
                    incidents_for_vapi.append(existing)
                continue

            incident = await _detect_service_down(db, service_name)
            if incident:
                new_incidents.append({
                    "id": incident.id,
                    "service_name": incident.service_name,
                    "severity": incident.severity,
                    "error_summary": incident.error_summary,
                })
                incidents_for_vapi.append(incident)

        # 2. Log-based detections
        sync_incidents = run_detection_cycle_sync(db)
        for incident in sync_incidents:
            new_incidents.append({
                "id": incident.id,
                "service_name": incident.service_name,
                "severity": incident.severity,
                "error_summary": incident.error_summary,
            })
            incidents_for_vapi.append(incident)

        # 3. Auto-trigger Vapi for all new/retried incidents while session is still alive
        for incident in incidents_for_vapi:
            await _trigger_vapi_for_incident(incident)

    finally:
        db.close()

    return new_incidents


async def watchdog_loop() -> None:
    """Background loop that continuously monitors for incidents."""
    logger.info(
        "Watchdog started — polling every %ds | latency threshold: %sms | exception threshold: %d",
        POLL_INTERVAL_SECONDS, LATENCY_THRESHOLD_MS, EXCEPTION_THRESHOLD,
    )
    while True:
        try:
            new_incidents = await run_detection_cycle()
            if new_incidents:
                for inc in new_incidents:
                    logger.info(
                        f"[WATCHDOG] New incident #{inc['id']} — "
                        f"{inc['service_name']} — {inc['severity']} — "
                        f"{inc['error_summary'][:80]}"
                    )
        except Exception as exc:
            logger.error(f"Watchdog error: {exc}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)