"""Cron job tool for scheduling background jobs from user requests (e.g. reminders)."""

import re
from datetime import datetime
from typing import Any, Dict, Optional
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from dateutil.tz import UTC

from backend.tools.base import BaseTool, ToolPermission, ToolResult
from backend.models import get_db, CronJob, User
import logging

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

logger = logging.getLogger(__name__)

# Weekday names for "next Friday" style parsing
_WEEKDAY_NAMES = (
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "mon", "tue", "wed", "thu", "fri", "sat", "sun",
)


def _parse_run_at(run_at_str: str, tz_name: Optional[str] = None) -> datetime:
    """Parse run_at string; if result is in the past and string looks relative, advance to next occurrence.
    Naive datetimes are interpreted in the user's timezone (tz_name, e.g. 'Asia/Tehran') or system local if not set."""
    now = datetime.now(UTC)
    run_at = date_parser.parse(run_at_str, default=now)
    if run_at.tzinfo is None:
        if tz_name and tz_name.strip():
            # User's timezone (e.g. Asia/Tehran) so "7:33 PM" means 7:33 PM in their location
            try:
                run_at = run_at.replace(tzinfo=ZoneInfo(tz_name.strip())).astimezone(UTC)
            except Exception:
                run_at = run_at.astimezone(UTC)
        else:
            run_at = run_at.astimezone(UTC)
    else:
        run_at = run_at.astimezone(UTC)
    if run_at > now:
        return run_at
    if re.search(r"\b(19|20)\d{2}\b", run_at_str):
        return run_at
    lower = run_at_str.lower()
    if "tomorrow" in lower:
        run_at = run_at + relativedelta(days=1)
        return run_at
    for wd in _WEEKDAY_NAMES:
        if wd in lower:
            run_at = run_at + relativedelta(weeks=1)
            if run_at > now:
                return run_at
            run_at = run_at + relativedelta(weeks=1)
            return run_at
    if "next" in lower:
        run_at = run_at + relativedelta(weeks=1)
        return run_at
    run_at = run_at + relativedelta(days=7)
    return run_at


class ScheduleJobTool(BaseTool):
    """
    Create a scheduled job or reminder. Use this tool whenever the user asks to be reminded
    of something at a specific time, to schedule a one-off task, or to set up a recurring task.
    The model decides from the conversation whether to call this tool; no other logic forces it.
    """

    @property
    def name(self) -> str:
        return "schedule_job"

    @property
    def description(self) -> str:
        return (
            "Create a scheduled job or reminder. Use when the user asks to be reminded of something "
            "(e.g. 'remind me to X', 'remind to X on DATE at TIME'), or to run a task at a specific "
            "date/time or on a schedule. Creates a one-shot job with run_at, or recurring with cron_expression. "
            "Args: job_type (e.g. 'reminder'), title, run_at (e.g. '2026-02-09 11:45' or 'tomorrow 9am'), "
            "optional cron_expression, schedule_timezone, payload (e.g. {\"body\": \"...\"})."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "job_type": {
                    "type": "string",
                    "description": "Type of job, e.g. 'reminder'. Use 'reminder' for 'remind me to X at Y'.",
                },
                "title": {
                    "type": "string",
                    "description": "Short title (e.g. 'Buy milk', 'Call John')",
                },
                "run_at": {
                    "type": "string",
                    "description": "When to run (first run for recurring). Examples: '2025-02-10 17:00', 'Friday 5pm', 'tomorrow at 9am'",
                },
                "cron_expression": {
                    "type": "string",
                    "description": "Optional. 5-field cron for recurring, e.g. '0 7 * * *' (daily 7am). If set, job reschedules after each run.",
                },
                "schedule_timezone": {
                    "type": "string",
                    "description": "Optional. IANA timezone for cron, e.g. 'America/Los_Angeles'. Default UTC.",
                },
                "payload": {
                    "type": "object",
                    "description": "Optional extra data; for reminder use {\"body\": \"longer description\"}",
                },
            },
            "required": ["job_type", "title", "run_at"],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.SAFE

    async def execute(self, **kwargs) -> ToolResult:
        job_type = (kwargs.get("job_type") or "reminder").strip().lower()
        title = kwargs.get("title", "").strip()
        run_at_str = kwargs.get("run_at", "").strip()
        cron_expression = (kwargs.get("cron_expression") or "").strip() or None
        schedule_timezone = (kwargs.get("schedule_timezone") or "").strip() or None
        payload = kwargs.get("payload")
        if isinstance(payload, dict):
            payload = {k: v for k, v in payload.items() if v is not None}
        elif isinstance(payload, str):
            try:
                import json
                payload = json.loads(payload)
                if isinstance(payload, dict):
                    payload = {k: v for k, v in payload.items() if v is not None}
                else:
                    payload = None
            except Exception:
                payload = None
        else:
            payload = None
        user_id = kwargs.get("user_id")

        if not title:
            return ToolResult(success=False, output=None, error="Title is required")
        if not run_at_str:
            return ToolResult(success=False, output=None, error="run_at is required")
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context is required")

        # Load user to get timezone (reminders use user's location so "7:33 PM" = their local time)
        db = next(get_db())
        try:
            user = db.query(User).filter(User.id == user_id).first()
            user_tz = None
            if user and user.preferences:
                user_tz = (user.preferences.get("timezone") or "").strip() or None
            tz_name = user_tz or "UTC"
        finally:
            db.close()

        try:
            run_at = _parse_run_at(run_at_str, tz_name=tz_name)
            if run_at <= datetime.now(UTC):
                return ToolResult(
                    success=False,
                    output=None,
                    error=(
                        "That date/time is in the past. Please use a future date, "
                        "e.g. 'next Friday at 3pm' or 'tomorrow at 9am'."
                    ),
                )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Could not parse date/time '{run_at_str}': {e}",
            )

        source = kwargs.get("source", "chat")
        # Default job's schedule_timezone to user's timezone if not provided
        if not schedule_timezone and user_tz:
            schedule_timezone = user_tz
        # Store as naive UTC so SQLite and the cron runner compare correctly
        run_at_for_db = run_at.astimezone(UTC).replace(tzinfo=None) if run_at.tzinfo else run_at
        db = next(get_db())
        try:
            job = CronJob(
                user_id=user_id,
                title=title,
                job_type=job_type,
                next_run_at=run_at_for_db,
                cron_expression=cron_expression,
                schedule_timezone=schedule_timezone,
                payload=payload,
                status="scheduled",
                source=source,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            return ToolResult(
                success=True,
                output={
                    "id": job.id,
                    "job_type": job.job_type,
                    "title": job.title,
                    "next_run_at": job.next_run_at.isoformat(),
                    "message": f"Scheduled {job.job_type} for {job.next_run_at.strftime('%Y-%m-%d %H:%M')}",
                },
            )
        except Exception as e:
            db.rollback()
            logger.exception("Schedule job failed")
            return ToolResult(success=False, output=None, error=str(e))
        finally:
            db.close()
