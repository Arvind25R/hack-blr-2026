from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.tables import AuditLog, ServiceState
from app.services.docker_controller import DockerController

router = APIRouter(prefix="/infra", tags=["infra"])

# Singleton controller instance
_controller = DockerController()


class ActionResponse(BaseModel):
    success: bool
    service_name: str
    action: str
    message: str
    details: Optional[str] = None


class ServiceStatusResponse(BaseModel):
    service_name: str
    status: str
    replicas: int
    details: Optional[str] = None


def _log_audit(db: Session, action: str, service_name: str, success: bool, details: str, incident_id: Optional[int] = None) -> None:
    audit = AuditLog(
        incident_id=incident_id,
        action=f"{action}:{service_name}",
        approved_by="system",
        details=f"success={success} | {details}",
    )
    db.add(audit)
    db.commit()


def _update_service_state(db: Session, service_name: str, status: str, replicas: int) -> None:
    state = db.query(ServiceState).filter(ServiceState.service_name == service_name).first()
    if state:
        state.status = status
        state.replicas = replicas
        state.last_checked = datetime.utcnow()
        state.updated_at = datetime.utcnow()
    else:
        state = ServiceState(
            service_name=service_name,
            status=status,
            replicas=replicas,
        )
        db.add(state)
    db.commit()


@router.post("/restart/{service_name}", response_model=ActionResponse)
def restart_service(
    service_name: str,
    incident_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    result = _controller.restart_service(service_name)

    _log_audit(db, "restart", service_name, result.success, result.message, incident_id)

    if result.success:
        _update_service_state(db, service_name, "running", 1)

    return {
        "success": result.success,
        "service_name": result.service_name,
        "action": result.action,
        "message": result.message,
        "details": result.details,
    }


@router.post("/scale/{service_name}", response_model=ActionResponse)
def scale_service(
    service_name: str,
    replicas: int = Query(2, ge=1, le=10),
    incident_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    result = _controller.scale_service(service_name, replicas)

    _log_audit(db, "scale", service_name, result.success, f"replicas={replicas} | {result.message}", incident_id)

    if result.success:
        _update_service_state(db, service_name, "running", replicas)

    return {
        "success": result.success,
        "service_name": result.service_name,
        "action": result.action,
        "message": result.message,
        "details": result.details,
    }


@router.get("/status/{service_name}", response_model=ServiceStatusResponse)
def get_service_status(service_name: str, db: Session = Depends(get_db)) -> dict:
    status = _controller.get_status(service_name)

    _update_service_state(db, service_name, status.status, status.replicas)

    return {
        "service_name": status.service_name,
        "status": status.status,
        "replicas": status.replicas,
        "details": status.details,
    }


@router.get("/status", response_model=list[ServiceStatusResponse])
def get_all_statuses(db: Session = Depends(get_db)) -> list[dict]:
    statuses = _controller.get_all_statuses()

    for s in statuses:
        _update_service_state(db, s.service_name, s.status, s.replicas)

    return [
        {
            "service_name": s.service_name,
            "status": s.status,
            "replicas": s.replicas,
            "details": s.details,
        }
        for s in statuses
    ]