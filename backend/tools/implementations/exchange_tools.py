"""Exchange (EWS) tools: email, calendar, tasks using user-configured Exchange settings."""

import datetime
from typing import Any, Dict, Optional

from backend.tools.base import BaseTool, ToolPermission, ToolResult

try:
    from exchangelib import (
        Credentials,
        Configuration,
        Account,
        DELEGATE,
        Message,
        Mailbox,
        CalendarItem,
        EWSTimeZone,
        EWSDateTime,
        Task,
    )
    EWS_AVAILABLE = True
except ImportError:
    EWS_AVAILABLE = False

import logging

logger = logging.getLogger(__name__)

# Tool names for Exchange; used by executor to add when user has Exchange enabled
EXCHANGE_TOOL_NAMES = [
    "exchange_list_emails",
    "exchange_get_email",
    "exchange_send_email",
    "exchange_list_calendar",
    "exchange_create_event",
    "exchange_list_tasks",
    "exchange_create_task",
]


def _get_account_for_user(user_id: int):
    """Load Exchange account from user's exchange_config. Returns (account, error_message)."""
    if not EWS_AVAILABLE:
        return None, "exchangelib is not installed"
    from backend.models import SessionLocal, User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None, "User not found"
        prefs = user.preferences or {}
        exchange = prefs.get("exchange_config", {})
        if not exchange.get("enabled"):
            return None, "Exchange is not enabled in settings"
        server = exchange.get("server")
        email = exchange.get("email")
        username = exchange.get("username")
        password = exchange.get("password")
        if not all([server, email, username, password]):
            return None, "Exchange server, email, username, and password must be set in Settings"
        creds = Credentials(username=username, password=password)
        config = Configuration(server=server, credentials=creds)
        account = Account(
            primary_smtp_address=email,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )
        return account, None
    except Exception as e:
        logger.exception("Exchange account setup failed")
        return None, str(e)
    finally:
        db.close()


class ExchangeListEmailsTool(BaseTool):
    """List latest email subjects from the user's Exchange inbox."""

    @property
    def name(self) -> str:
        return "exchange_list_emails"

    @property
    def description(self) -> str:
        return "Return latest email subjects from the user's Exchange inbox. Requires Exchange to be configured in Settings."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max number of emails to return", "default": 10},
            },
            "required": [],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(self, limit: int = 10, user_id: Optional[int] = None, **kwargs) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            results = []
            for item in account.inbox.all().order_by("-datetime_received")[:limit]:
                results.append(f"{item.subject} ({item.sender.email_address})")
            return ToolResult(success=True, output=results)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ExchangeGetEmailTool(BaseTool):
    """Get full details of one email from the inbox by position."""

    @property
    def name(self) -> str:
        return "exchange_get_email"

    @property
    def description(self) -> str:
        return (
            "Get full details of one email from the inbox by position. "
            "Index 1 = latest email, 2 = second latest, etc. Returns subject, from, to, date, and body."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "Position in inbox (1 = latest)", "default": 1},
            },
            "required": ["index"],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(self, index: int = 1, user_id: Optional[int] = None, **kwargs) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            items = list(account.inbox.all().order_by("-datetime_received"))
            if index < 1 or index > len(items):
                return ToolResult(
                    success=True,
                    output=f"No email at position {index}. Inbox has {len(items)} message(s). Use index 1 to {max(1, len(items))}.",
                )
            item = items[index - 1]
            from_addr = getattr(item.sender, "email_address", None) or getattr(item.sender, "address", str(item.sender))
            to_list = []
            for r in item.to_recipients or []:
                to_list.append(getattr(r, "email_address", None) or getattr(r, "address", str(r)))
            to_str = ", ".join(to_list) if to_list else ""
            body_obj = getattr(item, "body", None)
            if body_obj is not None and getattr(body_obj, "content", None) is not None:
                body_text = body_obj.content if isinstance(body_obj.content, str) else str(body_obj.content)
            else:
                body_text = str(body_obj) if body_obj else ""
            lines = [
                f"Subject: {item.subject or '(no subject)'}",
                f"From: {from_addr}",
                f"To: {to_str or '(none)'}",
                f"Date: {item.datetime_received}",
                f"Read: {getattr(item, 'is_read', '')}",
                "",
                "Body:",
                body_text or "(empty)",
            ]
            return ToolResult(success=True, output="\n".join(lines))
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ExchangeSendEmailTool(BaseTool):
    """Send an email via Exchange."""

    @property
    def name(self) -> str:
        return "exchange_send_email"

    @property
    def description(self) -> str:
        return "Send an email via the user's Exchange account. Requires Exchange configured in Settings."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to_address": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to_address", "subject", "body"],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(
        self,
        to_address: str,
        subject: str,
        body: str,
        user_id: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            msg = Message(
                account=account,
                subject=subject,
                body=body,
                to_recipients=[Mailbox(email_address=to_address)],
            )
            msg.send_and_save()
            return ToolResult(success=True, output="Email sent!")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ExchangeListCalendarTool(BaseTool):
    """List calendar items between two ISO timestamps."""

    @property
    def name(self) -> str:
        return "exchange_list_calendar"

    @property
    def description(self) -> str:
        return "List calendar events between two ISO datetime strings (e.g. 2025-02-01T00:00:00 and 2025-02-28T23:59:59)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_iso": {"type": "string", "description": "Start datetime in ISO format"},
                "end_iso": {"type": "string", "description": "End datetime in ISO format"},
            },
            "required": ["start_iso", "end_iso"],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(
        self,
        start_iso: str,
        end_iso: str,
        user_id: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            tz = EWSTimeZone("UTC")
            start = EWSDateTime.fromisoformat(start_iso).astimezone(tz)
            end = EWSDateTime.fromisoformat(end_iso).astimezone(tz)
            items = []
            for event in account.calendar.view(start=start, end=end):
                items.append(f"{event.start} — {event.subject}")
            return ToolResult(success=True, output=items)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ExchangeCreateEventTool(BaseTool):
    """Create a new calendar event."""

    @property
    def name(self) -> str:
        return "exchange_create_event"

    @property
    def description(self) -> str:
        return "Create a new calendar event. Provide start and end as ISO datetimes, plus subject and optional body."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "start_iso": {"type": "string", "description": "Start datetime in ISO format"},
                "end_iso": {"type": "string", "description": "End datetime in ISO format"},
                "subject": {"type": "string", "description": "Event subject"},
                "body": {"type": "string", "description": "Event body", "default": ""},
            },
            "required": ["start_iso", "end_iso", "subject"],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(
        self,
        start_iso: str,
        end_iso: str,
        subject: str,
        body: str = "",
        user_id: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            tz = EWSTimeZone("UTC")
            start = EWSDateTime.fromisoformat(start_iso).astimezone(tz)
            end = EWSDateTime.fromisoformat(end_iso).astimezone(tz)
            event = CalendarItem(
                account=account,
                folder=account.calendar,
                start=start,
                end=end,
                subject=subject,
                body=body or "",
            )
            event.save()
            return ToolResult(success=True, output=f"Created event: {subject}")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ExchangeListTasksTool(BaseTool):
    """List tasks from Exchange."""

    @property
    def name(self) -> str:
        return "exchange_list_tasks"

    @property
    def description(self) -> str:
        return "List tasks from the user's Exchange account with optional limit."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max number of tasks to return", "default": 10},
            },
            "required": [],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(self, limit: int = 10, user_id: Optional[int] = None, **kwargs) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            tasks = [
                f"{t.subject} | Due: {t.due_date} | Status: {t.status}"
                for t in account.tasks.all().order_by("due_date")[:limit]
            ]
            return ToolResult(success=True, output=tasks)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))


class ExchangeCreateTaskTool(BaseTool):
    """Create a new task in Exchange."""

    @property
    def name(self) -> str:
        return "exchange_create_task"

    @property
    def description(self) -> str:
        return "Create a new task. Provide subject, due date in ISO format, and optional body."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Task subject"},
                "due_iso": {"type": "string", "description": "Due date/datetime in ISO format"},
                "body": {"type": "string", "description": "Task body", "default": ""},
            },
            "required": ["subject", "due_iso"],
        }

    @property
    def permission(self) -> ToolPermission:
        return ToolPermission.NETWORK

    async def execute(
        self,
        subject: str,
        due_iso: str,
        body: str = "",
        user_id: Optional[int] = None,
        **kwargs,
    ) -> ToolResult:
        if user_id is None:
            return ToolResult(success=False, output=None, error="User context required")
        account, err = _get_account_for_user(user_id)
        if err:
            return ToolResult(success=False, output=None, error=err)
        try:
            due = datetime.datetime.fromisoformat(due_iso)
            t = Task(account=account, subject=subject, body=body or "", due_date=due)
            t.save()
            return ToolResult(success=True, output="Task created")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))
