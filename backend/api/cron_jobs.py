"""Cron Jobs API - CRUD and list for scheduled jobs created by the chatbot."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dateutil import parser as date_parser
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models import get_db, User, CronJob, CronJobRun, UserNotification
from backend.auth import get_current_user

router = APIRouter()


class NotificationResponse(BaseModel):
    id: int
    title: str
    body: Optional[str]
    cron_job_id: Optional[int]
    created_at: str
    read_at: Optional[str]


class CronJobCreate(BaseModel):
    title: str
    job_type: str = "reminder"
    next_run_at: str  # ISO or natural; for recurring, first run
    cron_expression: Optional[str] = None  # e.g. "0 7 * * *" for recurring
    schedule_timezone: Optional[str] = None  # IANA e.g. "America/Los_Angeles"
    payload: Optional[Dict[str, Any]] = None
    source: Optional[str] = "ui"


class CronJobUpdate(BaseModel):
    title: Optional[str] = None
    next_run_at: Optional[str] = None
    cron_expression: Optional[str] = None
    schedule_timezone: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class CronJobResponse(BaseModel):
    id: int
    title: str
    job_type: str
    next_run_at: str
    cron_expression: Optional[str]
    schedule_timezone: Optional[str]
    payload: Optional[Dict[str, Any]]
    status: str
    source: str
    created_at: str
    last_run_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]


class CronJobRunResponse(BaseModel):
    id: int
    cron_job_id: int
    run_at: str
    success: bool
    error_message: Optional[str]
    created_at: str


def _parse_dt(s: str) -> datetime:
    dt = date_parser.parse(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/", response_model=List[CronJobResponse])
async def list_cron_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status_filter: Optional[str] = Query(None, alias="status"),
    job_type_filter: Optional[str] = Query(None, alias="job_type"),
    limit: int = 50,
    offset: int = 0,
):
    """List cron jobs for the current user. Filter by status and/or job_type."""
    q = db.query(CronJob).filter(CronJob.user_id == current_user.id)
    if status_filter:
        q = q.filter(CronJob.status == status_filter)
    if job_type_filter:
        q = q.filter(CronJob.job_type == job_type_filter)
    jobs = q.order_by(CronJob.next_run_at.desc()).limit(limit).offset(offset).all()
    return [_job_response(j) for j in jobs]


@router.post("/", response_model=CronJobResponse, status_code=status.HTTP_201_CREATED)
async def create_cron_job(
    body: CronJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a cron job (e.g. from UI)."""
    try:
        next_run_at = _parse_dt(body.next_run_at)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid next_run_at: {e}")
    if next_run_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="next_run_at must be in the future")
    job = CronJob(
        user_id=current_user.id,
        title=body.title.strip(),
        job_type=(body.job_type or "reminder").strip().lower(),
        next_run_at=next_run_at,
        cron_expression=body.cron_expression.strip() if body.cron_expression else None,
        schedule_timezone=body.schedule_timezone.strip() if body.schedule_timezone else None,
        payload=body.payload,
        status="scheduled",
        source=body.source or "ui",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_response(job)


@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    unread_only: bool = Query(False, alias="unread_only"),
    limit: int = 50,
    offset: int = 0,
):
    """List in-app notifications (e.g. delivered reminders) for the current user."""
    q = db.query(UserNotification).filter(UserNotification.user_id == current_user.id)
    if unread_only:
        q = q.filter(UserNotification.read_at.is_(None))
    notifications = q.order_by(UserNotification.created_at.desc()).limit(limit).offset(offset).all()
    return [
        NotificationResponse(
            id=n.id,
            title=n.title,
            body=n.body,
            cron_job_id=n.cron_job_id,
            created_at=n.created_at.isoformat() if n.created_at else "",
            read_at=n.read_at.isoformat() if n.read_at else None,
        )
        for n in notifications
    ]


@router.patch("/notifications/{notification_id}", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    n = (
        db.query(UserNotification)
        .filter(UserNotification.id == notification_id, UserNotification.user_id == current_user.id)
        .first()
    )
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(n)
    return NotificationResponse(
        id=n.id,
        title=n.title,
        body=n.body,
        cron_job_id=n.cron_job_id,
        created_at=n.created_at.isoformat() if n.created_at else "",
        read_at=n.read_at.isoformat() if n.read_at else None,
    )


@router.get("/{job_id}/runs", response_model=List[CronJobRunResponse])
async def list_cron_job_runs(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """List run history for a cron job (OpenClaw-style)."""
    j = (
        db.query(CronJob)
        .filter(CronJob.id == job_id, CronJob.user_id == current_user.id)
        .first()
    )
    if not j:
        raise HTTPException(status_code=404, detail="Cron job not found")
    runs = (
        db.query(CronJobRun)
        .filter(CronJobRun.cron_job_id == job_id)
        .order_by(CronJobRun.run_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [
        CronJobRunResponse(
            id=r.id,
            cron_job_id=r.cron_job_id,
            run_at=r.run_at.isoformat() if r.run_at else "",
            success=r.success,
            error_message=r.error_message,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in runs
    ]


@router.get("/{job_id}", response_model=CronJobResponse)
async def get_cron_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single cron job."""
    j = (
        db.query(CronJob)
        .filter(CronJob.id == job_id, CronJob.user_id == current_user.id)
        .first()
    )
    if not j:
        raise HTTPException(status_code=404, detail="Cron job not found")
    return _job_response(j)


@router.patch("/{job_id}", response_model=CronJobResponse)
async def update_cron_job(
    job_id: int,
    body: CronJobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a cron job (e.g. cancel or reschedule)."""
    j = (
        db.query(CronJob)
        .filter(CronJob.id == job_id, CronJob.user_id == current_user.id)
        .first()
    )
    if not j:
        raise HTTPException(status_code=404, detail="Cron job not found")
    if j.status != "scheduled":
        raise HTTPException(status_code=400, detail="Can only update scheduled jobs")
    if body.title is not None:
        j.title = body.title.strip()
    if body.payload is not None:
        j.payload = body.payload
    if body.next_run_at is not None:
        try:
            j.next_run_at = _parse_dt(body.next_run_at)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid next_run_at: {e}")
    if body.cron_expression is not None:
        j.cron_expression = body.cron_expression.strip() or None
    if body.schedule_timezone is not None:
        j.schedule_timezone = body.schedule_timezone.strip() or None
    if body.status is not None and body.status in ("scheduled", "cancelled"):
        j.status = body.status
    db.commit()
    db.refresh(j)
    return _job_response(j)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cron_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a cron job."""
    j = (
        db.query(CronJob)
        .filter(CronJob.id == job_id, CronJob.user_id == current_user.id)
        .first()
    )
    if not j:
        raise HTTPException(status_code=404, detail="Cron job not found")
    db.delete(j)
    db.commit()


def _job_response(j: CronJob) -> CronJobResponse:
    return CronJobResponse(
        id=j.id,
        title=j.title,
        job_type=j.job_type,
        next_run_at=j.next_run_at.isoformat() if j.next_run_at else "",
        cron_expression=j.cron_expression,
        schedule_timezone=getattr(j, "schedule_timezone", None),
        payload=j.payload,
        status=j.status,
        source=j.source,
        created_at=j.created_at.isoformat() if j.created_at else "",
        last_run_at=j.last_run_at.isoformat() if j.last_run_at else None,
        completed_at=j.completed_at.isoformat() if j.completed_at else None,
        error_message=j.error_message,
    )
