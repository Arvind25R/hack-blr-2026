import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import SessionLocal
from app.models.tables import Incident, Log
from app.services.qdrant_service import get_best_solution

logger = logging.getLogger("watchdog")

# Detection thresholds
ERROR_RATE_THRESHOLD = 0.5  # 50% error rate triggers incident
MIN_LOGS_FOR_DETECTION = 3  # minimum logs in window to evaluate
LATENCY_THRESHOLD_MS = 4000.0  # avg latency above this triggers incident
WINDOW_SECONDS = 30  # sliding window size
POLL_INTERVAL_SECONDS = 10  # how often watchdog checks

SERVICES = ["service-a", "service-b", "service-c"]


def _get_recent_logs(db: Session, service_name: str, window_seconds: int) -> list[Log]:
    cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
    return (
        db.query(Log)
        .filter(Log.service_name == service_name, Log.timestamp >= cutoff)
        .all()
    )


def _has_active_incident(db: Session, service_name: str) -> bool:
    """Check if there's already an unresolved incident for this service."""
    active_statuses = ["DETECTED", "ANALYZED", "USER_NOTIFIED", "APPROVED", "ACTION_TAKEN"]
    return (
        db.query(Incident)
        .filter(Incident.service_name == service_name, Incident.status.in_(active_statuses))
        .first()
        is not None
    )

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


def _detect_high_error_rate(db: Session, service_name: str, logs: list[Log]) -> Optional[Incident]:
    if len(logs) < MIN_LOGS_FOR_DETECTION:
        return None

    error_count = sum(1 for log in logs if log.status == "ERROR")
    error_rate = error_count / len(logs)

    if error_rate >= ERROR_RATE_THRESHOLD:
        latest_error = next((log for log in reversed(logs) if log.status == "ERROR"), None)
        error_types = set(log.error_type for log in logs if log.error_type)
        summary = (
            f"High error rate detected: {error_rate:.0%} "
            f"({error_count}/{len(logs)} requests failed in last {WINDOW_SECONDS}s). "
            f"Error types: {', '.join(error_types) or 'unknown'}"
        )
        return _create_incident(
            db,
            service_name,
            severity="high" if error_rate >= 0.8 else "medium",
            error_summary=summary,
            trace_id=latest_error.trace_id if latest_error else None,
        )
    return None


def _detect_service_down(db: Session, service_name: str, logs: list[Log]) -> Optional[Incident]:
    if len(logs) == 0:
        return None

    # All logs are errors → service likely down
    if all(log.status == "ERROR" for log in logs) and len(logs) >= MIN_LOGS_FOR_DETECTION:
        connection_errors = [log for log in logs if log.error_type in ("connection_error", "timeout")]
        if connection_errors:
            summary = (
                f"Service appears DOWN: all {len(logs)} requests failed in last {WINDOW_SECONDS}s. "
                f"Connection/timeout errors detected."
            )
            return _create_incident(
                db, service_name, severity="critical", error_summary=summary,
                trace_id=logs[-1].trace_id,
            )
    return None


def _detect_latency_spike(db: Session, service_name: str, logs: list[Log]) -> Optional[Incident]:
    if len(logs) < MIN_LOGS_FOR_DETECTION:
        return None

    durations = [log.duration_ms for log in logs if log.duration_ms is not None]
    if not durations:
        return None

    avg_duration = sum(durations) / len(durations)
    latency_logs = [log for log in logs if log.status == "LATENCY"]

    if avg_duration >= LATENCY_THRESHOLD_MS or len(latency_logs) >= 2:
        summary = (
            f"Latency spike detected: avg response time {avg_duration:.0f}ms "
            f"(threshold: {LATENCY_THRESHOLD_MS:.0f}ms). "
            f"{len(latency_logs)} high-latency requests in last {WINDOW_SECONDS}s."
        )
        return _create_incident(
            db, service_name, severity="medium", error_summary=summary,
            trace_id=logs[-1].trace_id,
        )
    return None

def run_detection_cycle() -> list[dict]:
    """Run one full detection cycle across all services. Returns new incident summaries."""
    db = SessionLocal()
    new_incidents: list[dict] = []

    try:
        for service_name in SERVICES:
            if _has_active_incident(db, service_name):
                continue

            logs = _get_recent_logs(db, service_name, WINDOW_SECONDS)

            # Check in priority order: service down > high error rate > latency spike
            incident = _detect_service_down(db, service_name, logs)
            if incident:
                new_incidents.append({
                    "id": incident.id,
                    "service_name": incident.service_name,
                    "severity": incident.severity,
                    "error_summary": incident.error_summary,
                })
                continue

            incident = _detect_high_error_rate(db, service_name, logs)
            if incident:
                new_incidents.append({
                    "id": incident.id,
                    "service_name": incident.service_name,
                    "severity": incident.severity,
                    "error_summary": incident.error_summary,
                })
                continue

            incident = _detect_latency_spike(db, service_name, logs)
            if incident:
                new_incidents.append({
                    "id": incident.id,
                    "service_name": incident.service_name,
                    "severity": incident.severity,
                    "error_summary": incident.error_summary,
                })

    finally:
        db.close()

    return new_incidents


async def watchdog_loop() -> None:
    """Background loop that continuously monitors for incidents."""
    logger.info("Watchdog started — polling every %d seconds", POLL_INTERVAL_SECONDS)
    while True:
        try:
            new_incidents = run_detection_cycle()
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