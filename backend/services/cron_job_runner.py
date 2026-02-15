"""Runner for scheduled cron jobs created by the chatbot (OpenClaw-style: persist, recurring, run history)."""

import logging
import threading
from datetime import datetime, timezone
from typing import Optional

from backend.models import get_db, CronJob, CronJobRun, TelegramPairing, UserNotification
from backend.config import settings

logger = logging.getLogger(__name__)

_runner_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def _send_telegram_message(chat_id: int, text: str) -> tuple[bool, Optional[str]]:
    """Send a text message via Telegram Bot API. Returns (success, error_detail)."""
    token = (getattr(settings, "TELEGRAM_BOT_TOKEN", None) or "").strip()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set; cannot send Telegram reminder")
        return False, "Bot token not set. Add TELEGRAM_BOT_TOKEN to .env and enable ENABLE_TELEGRAM_BOT."
    try:
        import httpx
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        with httpx.Client(timeout=10.0) as client:
            r = client.post(api_url, json=payload)
            if r.status_code != 200:
                try:
                    err = r.json()
                    detail = err.get("description", r.text[:200])
                except Exception:
                    detail = r.text[:200] if r.text else f"HTTP {r.status_code}"
                logger.warning("Telegram sendMessage failed: %s %s", r.status_code, detail)
                return False, f"Telegram API: {detail}"
            return True, None
    except Exception as e:
        logger.exception("Telegram send failed: %s", e)
        return False, str(e)


def _get_next_run_from_cron(cron_expression: str, after: datetime, tz_name: Optional[str] = None) -> Optional[datetime]:
    """Compute next run time from cron expression (OpenClaw-style). Returns UTC datetime."""
    if not cron_expression or not cron_expression.strip():
        return None
    try:
        from croniter import croniter
        from zoneinfo import ZoneInfo
        ref_tz = ZoneInfo(tz_name or "UTC")
        # after may be UTC; convert to ref tz for croniter
        after_local = after.astimezone(ref_tz)
        it = croniter(cron_expression.strip(), after_local)
        next_local = it.get_next(datetime)
        if next_local.tzinfo is None:
            next_local = next_local.replace(tzinfo=ref_tz)
        return next_local.astimezone(timezone.utc)
    except Exception as e:
        logger.warning("croniter failed for %s: %s", cron_expression, e)
        return None


def _run_job(db, job: CronJob) -> None:
    """Execute a single job by job_type. Reschedule if recurring (cron_expression)."""
    now = datetime.now(timezone.utc)
    job.status = "running"
    job.last_run_at = now
    db.commit()

    run_success = False
    run_error = None
    try:
        if job.job_type == "reminder":
            # Always create an in-app notification so the user sees the reminder in the UI
            body = None
            if job.payload and isinstance(job.payload, dict) and job.payload.get("body"):
                body = job.payload["body"]
            notification = UserNotification(
                user_id=job.user_id,
                title=job.title,
                body=body,
                cron_job_id=job.id,
            )
            db.add(notification)
            db.commit()

            # Try to send via Telegram if paired (DM the user)
            pairing = (
                db.query(TelegramPairing)
                .filter(
                    TelegramPairing.user_id == job.user_id,
                    TelegramPairing.telegram_user_id.isnot(None),
                )
                .first()
            )
            # Friendly reminder DM so the user gets "hey, you have to do that thing!"
            msg_text = f"Hey! Reminder: you asked to do this — {job.title}."
            if body:
                msg_text += f"\n\n{body}"
            if pairing and pairing.telegram_user_id:
                telegram_sent, telegram_error = _send_telegram_message(int(pairing.telegram_user_id), msg_text)
                if telegram_sent:
                    logger.info("Reminder job %s sent to Telegram for user %s (chat_id=%s)", job.id, job.user_id, pairing.telegram_user_id)
                else:
                    job.error_message = (
                        f"Reminder saved in app but Telegram failed: {telegram_error}"
                        if telegram_error
                        else "Reminder saved in app but could not send to Telegram. Check bot token and pairing."
                    )
                    logger.warning("Reminder job %s: Telegram not sent for user %s: %s", job.id, job.user_id, job.error_message)
            else:
                job.error_message = "Reminder delivered in app only. Pair Telegram in Settings → Telegram (send /pair YOUR_CODE to the bot) to get reminders there too."
                logger.info("Reminder job %s: no Telegram pairing for user %s; delivered in-app only", job.id, job.user_id)

            run_success = True
        else:
            logger.warning("Unknown job_type %s for job %s", job.job_type, job.id)
            run_error = f"Unknown job_type: {job.job_type}"
            job.status = "failed"
            job.error_message = run_error
            db.commit()
            db.add(CronJobRun(cron_job_id=job.id, run_at=now, success=False, error_message=run_error))
            db.commit()
            return

        # Recurring: reschedule if cron_expression is set (OpenClaw-style)
        next_run = _get_next_run_from_cron(
            job.cron_expression or "",
            now,
            getattr(job, "schedule_timezone", None) or None,
        )
        if next_run is not None:
            job.next_run_at = next_run
            job.status = "scheduled"
            job.completed_at = None
            job.error_message = None  # clear so next run doesn't show old message
            logger.info("Recurring job %s rescheduled for %s", job.id, next_run.isoformat())
        else:
            job.status = "completed"
            job.completed_at = now
        # Run history (OpenClaw-style cron runs)
        db.add(CronJobRun(cron_job_id=job.id, run_at=now, success=run_success, error_message=None))
        db.commit()
    except Exception as e:
        logger.exception("Job %s failed: %s", job.id, e)
        run_error = str(e)
        job.status = "failed"
        job.error_message = run_error
        db.rollback()
        db.add(CronJobRun(cron_job_id=job.id, run_at=now, success=False, error_message=run_error))
        db.commit()


def _process_due_jobs() -> None:
    """Find scheduled jobs that are due and run them."""
    db = next(get_db())
    try:
        now = datetime.now(timezone.utc)
        # Use naive UTC for filter so SQLite (which stores naive) compares correctly
        now_naive_utc = now.replace(tzinfo=None) if now.tzinfo else now
        due = (
            db.query(CronJob)
            .filter(CronJob.status == "scheduled", CronJob.next_run_at <= now_naive_utc)
            .order_by(CronJob.next_run_at.asc())
            .all()
        )
        if due:
            logger.info("Cron runner: processing %s due job(s)", len(due))
        for job in due:
            try:
                _run_job(db, job)
            except Exception as e:
                logger.exception("Failed to process job %s: %s", job.id, e)
                db.rollback()
    finally:
        db.close()


# How often to check for due jobs (seconds)
_RUNNER_INTERVAL_SEC = 30


def _runner_loop() -> None:
    """Run job check every _RUNNER_INTERVAL_SEC seconds."""
    logger.info("Cron job runner started (interval=%ss)", _RUNNER_INTERVAL_SEC)
    cycles = 0
    while not _stop_event.wait(timeout=_RUNNER_INTERVAL_SEC):
        cycles += 1
        try:
            _process_due_jobs()
        except Exception as e:
            logger.exception("Cron job run failed: %s", e)


def start_cron_job_runner() -> None:
    """Start the cron job runner thread."""
    global _runner_thread
    if _runner_thread is not None:
        return
    _stop_event.clear()
    _runner_thread = threading.Thread(target=_runner_loop, daemon=True)
    _runner_thread.start()
    logger.info("Cron job runner thread started")


def stop_cron_job_runner() -> None:
    """Stop the cron job runner thread."""
    global _runner_thread
    _stop_event.set()
    if _runner_thread is not None:
        _runner_thread.join(timeout=_RUNNER_INTERVAL_SEC + 5)
        _runner_thread = None
    logger.info("Cron job runner stopped")
