import datetime
from exchangelib import (
    Credentials, Configuration, Account,
    DELEGATE, Message, Mailbox, CalendarItem, EWSTimeZone, EWSDateTime, Task
)
from mcp.server.fastmcp import FastMCP

# ——— CONFIGURATION ———
# For standalone MCP server: set env vars EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD
# In-app: use Settings → Exchange in the UI; the backend uses in-process Exchange tools with those settings.
import os
SERVER = os.environ.get("EWS_SERVER", "")
EMAIL = os.environ.get("EWS_EMAIL", "")
USERNAME = os.environ.get("EWS_USERNAME", "")
PASSWORD = os.environ.get("EWS_PASSWORD", "")

# ——— SETUP EXCHANGE ACCOUNT ———
account = None
if SERVER and EMAIL and USERNAME and PASSWORD:
    creds = Credentials(username=USERNAME, password=PASSWORD)
    config = Configuration(server=SERVER, credentials=creds)
    account = Account(primary_smtp_address=EMAIL,
                      config=config,
                      autodiscover=False,
                      access_type=DELEGATE)

tz = EWSTimeZone("UTC")  # adjust to your timezone

def local_dt(year, month, day, hour, minute=0):
    return tz.localize(datetime.datetime(year, month, day, hour, minute))

# ——— MCP SERVER ———
mcp = FastMCP("ews_exchange_server")

# ——— TOOLS ———

@mcp.tool()
def list_emails(limit: int = 10) -> list[str]:
    """Return latest email subjects."""
    if account is None:
        return ["Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."]
    results = []
    for item in account.inbox.all().order_by("-datetime_received")[:limit]:
        results.append(f"{item.subject} ({item.sender.email_address})")
    return results


@mcp.tool()
def get_email(index: int = 1) -> str:
    """Get full details of one email from the inbox by position. Index 1 = latest email, 2 = second latest, etc. Returns subject, from, to, date, and full body."""
    if account is None:
        return "Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."
    items = list(account.inbox.all().order_by("-datetime_received"))
    if index < 1 or index > len(items):
        return f"No email at position {index}. Inbox has {len(items)} message(s). Use index 1 to {max(1, len(items))}."
    item = items[index - 1]
    from_addr = getattr(item.sender, "email_address", None) or getattr(item.sender, "address", str(item.sender))
    to_list = []
    for r in (item.to_recipients or []):
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
    return "\n".join(lines)


@mcp.tool()
def send_email(to_address: str, subject: str, body: str) -> str:
    """Send an email."""
    if account is None:
        return "Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."
    msg = Message(
        account=account,
        subject=subject,
        body=body,
        to_recipients=[Mailbox(email_address=to_address)]
    )
    msg.send_and_save()
    return "Email sent!"

@mcp.tool()
def list_calendar(start_iso: str, end_iso: str) -> list[str]:
    """List calendar items between two ISO timestamps."""
    if account is None:
        return ["Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."]
    # Parse ISO datetimes into EWSDateTime with UTC timezone
    tz = EWSTimeZone("UTC")
    start = EWSDateTime.fromisoformat(start_iso).astimezone(tz)
    end   = EWSDateTime.fromisoformat(end_iso).astimezone(tz)

    items = []
    for event in account.calendar.view(start=start, end=end):
        items.append(f"{event.start} — {event.subject}")
    return items

@mcp.tool()
def create_event(start_iso: str, end_iso: str, subject: str, body: str) -> str:
    """Create a new calendar event."""
    if account is None:
        return "Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."
    # Parse ISO datetimes into EWSDateTime with UTC timezone
    tz = EWSTimeZone("UTC")
    start = EWSDateTime.fromisoformat(start_iso).astimezone(tz)
    end   = EWSDateTime.fromisoformat(end_iso).astimezone(tz)

    event = CalendarItem(
        account=account,
        folder=account.calendar,
        start=start,
        end=end,
        subject=subject,
        body=body,
    )
    event.save()
    return f"Created event: {subject}"

@mcp.tool()
def list_tasks(limit: int = 10) -> list[str]:
    """Lists all available tasks with limit number"""
    if account is None:
        return ["Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."]
    return [f"{t.subject} | Due: {t.due_date} | Status: {t.status}" for t in account.tasks.all().order_by("due_date")[:limit]]

@mcp.tool()
def create_task(subject: str, due_iso: str, body: str = "") -> str:
    """Creates a new task."""
    if account is None:
        return "Error: Exchange not configured. Set EWS_SERVER, EWS_EMAIL, EWS_USERNAME, EWS_PASSWORD."
    from datetime import datetime
    due = datetime.fromisoformat(due_iso)
    t = Task(account=account, subject=subject, body=body, due_date=due)
    t.save()
    return "Task created"


# ——— RUN SERVER ———
if __name__ == "__main__":
    print("Starting EWS MCP server...")
    mcp.run()
