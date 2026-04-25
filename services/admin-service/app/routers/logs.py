from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import LogCreate, LogResponse
from app.models.tables import Log

router = APIRouter(prefix="/logs", tags=["logs"])


@router.post("/", response_model=LogResponse, status_code=201)
def ingest_log(log_data: LogCreate, db: Session = Depends(get_db)) -> Log:
    log_entry = Log(
        trace_id=log_data.trace_id,
        service_name=log_data.service_name,
        status=log_data.status,
        error_type=log_data.error_type,
        message=log_data.message,
        duration_ms=log_data.duration_ms,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


@router.get("/", response_model=list[LogResponse])
def get_logs(
    service: Optional[str] = Query(None),
    trace_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[Log]:
    query = db.query(Log)
    if service:
        query = query.filter(Log.service_name == service)
    if trace_id:
        query = query.filter(Log.trace_id == trace_id)
    if status:
        query = query.filter(Log.status == status)
    return query.order_by(desc(Log.timestamp)).limit(limit).all()