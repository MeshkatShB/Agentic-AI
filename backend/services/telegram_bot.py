"""Telegram bot service with username-based pairing. Only registered app users can use the bot after pairing."""

import asyncio
import logging
import secrets
import string
import threading
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

# Optional telegram imports - bot only runs if token is set
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Update = None
    ContextTypes = None
    InlineKeyboardButton = None
    InlineKeyboardMarkup = None
    CallbackQueryHandler = None

from backend.config import settings
from backend.models import get_db, User, Conversation, TelegramPairing
from backend.agent import agent_executor
from backend.tools import tool_registry

logger = logging.getLogger(__name__)

# Alphanumeric pairing code (avoid ambiguous chars)
CODE_CHARS = string.ascii_uppercase + string.digits
CODE_LENGTH = 8


def _generate_pairing_code() -> str:
    return "".join(secrets.choice(CODE_CHARS) for _ in range(CODE_LENGTH))


def generate_pairing_code() -> str:
    """Public helper to generate a new pairing code (for API)."""
    return _generate_pairing_code()


def get_or_create_telegram_conversation(db: Session, user: User) -> Conversation:
    """Get or create the dedicated Telegram conversation for this user."""
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user.id,
            Conversation.title == "Telegram",
        )
        .first()
    )
    if conv:
        return conv
    conv = Conversation(
        user_id=user.id,
        title="Telegram",
        model=(user.preferences or {}).get("model"),
        temperature=(user.preferences or {}).get("temperature"),
        max_steps=(user.preferences or {}).get("max_steps"),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_current_telegram_conversation(db: Session, user: User) -> Conversation:
    """Get the conversation to use for this Telegram user (current chat or default)."""
    from sqlalchemy.orm.attributes import flag_modified
    prefs = user.preferences or {}
    current_id = prefs.get("telegram_current_conversation_id")
    if current_id is not None:
        conv = db.query(Conversation).filter(
            Conversation.id == current_id,
            Conversation.user_id == user.id,
        ).first()
        if conv:
            return conv
    conv = get_or_create_telegram_conversation(db, user)
    # Persist default so /chats shows the right active chat
    prefs = user.preferences or {}
    prefs["telegram_current_conversation_id"] = conv.id
    user.preferences = prefs
    flag_modified(user, "preferences")
    db.commit()
    return conv


def get_telegram_conversations(db: Session, user: User, limit: int = 15) -> list:
    """List conversations that are Telegram chats (title 'Telegram' or 'Telegram - ...'), newest first."""
    from sqlalchemy import or_
    return (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user.id,
            or_(
                Conversation.title == "Telegram",
                Conversation.title.like("Telegram - %"),
            ),
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )


def get_user_by_telegram_id(db: Session, telegram_user_id: int) -> Optional[User]:
    """Resolve Telegram user id to app User via pairing."""
    pairing = (
        db.query(TelegramPairing)
        .filter(TelegramPairing.telegram_user_id == telegram_user_id)
        .first()
    )
    if not pairing:
        return None
    return db.query(User).filter(User.id == pairing.user_id).first()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start. If message has 'pair <code>', try to pair; else show instructions."""
    if not update.message or not update.message.text:
        await update.message.reply_text("Send /start to see instructions.")
        return

    text = update.message.text.strip()
    telegram_user_id = update.effective_user.id if update.effective_user else None
    telegram_username = (update.effective_user.username or "").strip() if update.effective_user else ""

    db: Session = next(get_db())
    try:
        # Check if already paired
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if user:
            await update.message.reply_text(
                f"You are already paired as **{user.username}**. Send any message to chat with the AI.",
                parse_mode="Markdown",
            )
            return

        # Try to parse "pair CODE" or "/start pair CODE"
        parts = text.split()
        code = None
        if len(parts) >= 2 and parts[1].lower() == "pair" and len(parts) >= 3:
            code = parts[2].strip().upper()
        elif len(parts) >= 2:
            code = parts[1].strip().upper()

        if not code:
            await update.message.reply_text(
                "This bot is only for registered users.\n\n"
                "1. Log in to the app and go to **Settings → Telegram**.\n"
                "2. Copy your pairing code.\n"
                "3. Send: /start pair YOUR_CODE\n\n"
                "Example: /start pair ABC12XYZ",
                parse_mode="Markdown",
            )
            return

        # Look up pairing by code
        pairing = db.query(TelegramPairing).filter(TelegramPairing.pairing_code == code).first()
        if not pairing:
            await update.message.reply_text("Invalid or expired pairing code. Get a new code from Settings → Telegram in the app.")
            return
        if pairing.telegram_user_id is not None:
            await update.message.reply_text("This code was already used. Get a new code from the app if you need to re-pair.")
            return

        # Pair: link this Telegram user to the app user
        pairing.telegram_user_id = telegram_user_id
        pairing.telegram_username = telegram_username or None
        pairing.paired_at = datetime.utcnow()
        db.commit()

        app_user = db.query(User).filter(User.id == pairing.user_id).first()
        await update.message.reply_text(
            f"Paired successfully as **{app_user.username}**. You can now send messages to chat with the AI.",
            parse_mode="Markdown",
        )
    finally:
        db.close()


async def cmd_pair(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pair CODE."""
    if not update.message or not context.args:
        await update.message.reply_text("Usage: /pair YOUR_CODE\nGet your code from Settings → Telegram in the app.")
        return

    code = context.args[0].strip().upper()
    telegram_user_id = update.effective_user.id if update.effective_user else None
    telegram_username = (update.effective_user.username or "").strip() if update.effective_user else ""

    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if user:
            await update.message.reply_text(f"You are already paired as **{user.username}**.", parse_mode="Markdown")
            return

        pairing = db.query(TelegramPairing).filter(TelegramPairing.pairing_code == code).first()
        if not pairing:
            await update.message.reply_text("Invalid or expired pairing code.")
            return
        if pairing.telegram_user_id is not None:
            await update.message.reply_text("This code was already used.")
            return

        pairing.telegram_user_id = telegram_user_id
        pairing.telegram_username = telegram_username or None
        pairing.paired_at = datetime.utcnow()
        db.commit()

        app_user = db.query(User).filter(User.id == pairing.user_id).first()
        await update.message.reply_text(
            f"Paired successfully as **{app_user.username}**. Send any message to chat with the AI.",
            parse_mode="Markdown",
        )
    finally:
        db.close()


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status - show pairing status."""
    if not update.message:
        return
    telegram_user_id = update.effective_user.id if update.effective_user else None
    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if user:
            await update.message.reply_text(
                f"**Status:** Paired\n**Account:** {user.username}\n\nSend any message to chat with the AI.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                "**Status:** Not paired\n\nUse /start or /pair YOUR_CODE to pair. Get your code from Settings → Telegram in the app.",
                parse_mode="Markdown",
            )
    finally:
        db.close()


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help - list commands."""
    if not update.message:
        return
    text = (
        "**Commands:**\n\n"
        "/start — Pairing instructions, or use /start pair YOUR_CODE to pair\n"
        "/pair YOUR_CODE — Pair your Telegram with the app\n"
        "/status — Show whether you are paired and with which account\n"
        "/tools — List and toggle which tools are active for Telegram\n"
        "/newchat — Start a new chat (fresh history, also appears in the app)\n"
        "/chats — List your Telegram chats and switch between them\n"
        "/help — Show this message\n\n"
        "After pairing, send any message to chat with the AI."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_newchat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /newchat - create a new conversation and set it as current."""
    if not update.message:
        return
    telegram_user_id = update.effective_user.id if update.effective_user else None
    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if not user:
            await update.message.reply_text(
                "You are not paired. Use /start pair YOUR_CODE first.",
                parse_mode="Markdown",
            )
            return
        from sqlalchemy.orm.attributes import flag_modified
        now = datetime.utcnow()
        title = f"Telegram - {now.strftime('%Y-%m-%d %H:%M')}"
        conv = Conversation(
            user_id=user.id,
            title=title,
            model=(user.preferences or {}).get("model"),
            temperature=(user.preferences or {}).get("temperature"),
            max_steps=(user.preferences or {}).get("max_steps"),
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        prefs = user.preferences or {}
        prefs["telegram_current_conversation_id"] = conv.id
        user.preferences = prefs
        flag_modified(user, "preferences")
        db.commit()
        await update.message.reply_text(
            f"**New chat created.**\n\nYou're now in a fresh conversation: _{title}_.\n"
            "Send a message to continue. Use /chats to switch between chats.",
            parse_mode="Markdown",
        )
    finally:
        db.close()


async def cmd_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /chats - list Telegram chats and let user switch with inline buttons."""
    if not update.message:
        return
    telegram_user_id = update.effective_user.id if update.effective_user else None
    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if not user:
            await update.message.reply_text(
                "You are not paired. Use /start pair YOUR_CODE first.",
                parse_mode="Markdown",
            )
            return
        prefs = user.preferences or {}
        current_id = prefs.get("telegram_current_conversation_id")
        conversations = get_telegram_conversations(db, user)
        if not conversations:
            await update.message.reply_text("No Telegram chats yet. Send /newchat to create one.", parse_mode="Markdown")
            return
        lines = ["**Your Telegram chats**\n\nTap a chat to switch to it.\n"]
        buttons = []
        for c in conversations:
            label = c.title or f"Chat {c.id}"
            if c.id == current_id:
                label = f"● {label}"
            # Telegram callback_data max 64 bytes
            buttons.append([InlineKeyboardButton(label, callback_data=f"chat_{c.id}")])
        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=keyboard)
    finally:
        db.close()


async def callback_chat_switch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button: switch to selected chat."""
    from sqlalchemy.orm.attributes import flag_modified

    query = update.callback_query
    if not query or not query.data or not query.data.startswith("chat_"):
        return
    await query.answer()
    try:
        conv_id = int(query.data[5:].strip())
    except ValueError:
        return
    telegram_user_id = update.effective_user.id if update.effective_user else None
    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if not user:
            await query.edit_message_text("Not paired. Use /start pair YOUR_CODE first.", parse_mode="Markdown")
            return
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.user_id == user.id,
        ).first()
        if not conv:
            await query.edit_message_text("That chat is no longer available.", parse_mode="Markdown")
            return
        prefs = user.preferences or {}
        prefs["telegram_current_conversation_id"] = conv.id
        user.preferences = prefs
        flag_modified(user, "preferences")
        db.commit()
        title = conv.title or f"Chat {conv.id}"
        await query.edit_message_text(
            f"Switched to: **{title}**\n\nSend a message to continue.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.exception("callback_chat_switch failed: %s", e)
        try:
            await query.edit_message_text("Something went wrong. Try /chats again.")
        except Exception:
            pass
    finally:
        db.close()


def _tools_active_set(user: User) -> set:
    """Return the set of tool names currently active for this user on Telegram."""
    allowed = set(user.allowed_tools or [])
    prefs = user.preferences or {}
    telegram_tools = prefs.get("telegram_tools")
    if telegram_tools is None:
        return allowed
    return set(telegram_tools)


def _build_tools_message_and_keyboard(user: User, db: Session) -> tuple:
    """Build message text and inline keyboard for /tools. Returns (text, InlineKeyboardMarkup)."""
    try:
        tool_registry.register_custom_tools_for_user(db, user.id)
    except Exception as e:
        logger.debug("Register custom tools for /tools: %s", e)
    allowed = list(user.allowed_tools or [])
    active = _tools_active_set(user)
    # Get tool names we can show (from registry); keep allowed order, use name only for keyboard
    tool_names = [t.name for t in tool_registry.get_tools_for_user(allowed)]
    if not tool_names:
        tool_names = sorted(allowed)
    lines = ["**Telegram tools**\n\nTap a tool to turn it ON or OFF. Only active tools are used when you chat here.\n"]
    buttons = []
    for name in sorted(tool_names):
        is_on = name in active
        label = f"{'✓' if is_on else '○'} {name}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"tools_{name}")])
    if not buttons:
        lines.append("_No tools available. Enable tools in the app under Settings → AI Settings._")
        return "\n".join(lines), None
    active_count = sum(1 for name in tool_names if name in active)
    lines.append(f"Active: **{active_count}** of **{len(tool_names)}**")
    keyboard = InlineKeyboardMarkup(buttons)
    return "\n".join(lines), keyboard


async def cmd_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tools - list available tools and let user toggle which are active."""
    if not update.message:
        return
    telegram_user_id = update.effective_user.id if update.effective_user else None
    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if not user:
            await update.message.reply_text(
                "You are not paired. Use /start pair YOUR_CODE first. Get your code from **Settings → Telegram** in the app.",
                parse_mode="Markdown",
            )
            return
        text, keyboard = _build_tools_message_and_keyboard(user, db)
        if keyboard is not None:
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await update.message.reply_text(text, parse_mode="Markdown")
    finally:
        db.close()


async def callback_tools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button press: toggle a tool on/off and update the message."""
    from sqlalchemy.orm.attributes import flag_modified

    query = update.callback_query
    if not query or not query.data or not query.data.startswith("tools_"):
        return
    await query.answer()
    tool_name = query.data[6:].strip()
    if not tool_name:
        return
    telegram_user_id = update.effective_user.id if update.effective_user else None
    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id) if telegram_user_id else None
        if not user:
            await query.edit_message_text("Not paired. Use /start pair YOUR_CODE first.", parse_mode="Markdown")
            return
        allowed = set(user.allowed_tools or [])
        if tool_name not in allowed:
            await query.answer("That tool is not in your allowed list. Change it in the app.", show_alert=True)
            return
        active = _tools_active_set(user)
        if tool_name in active:
            active.discard(tool_name)
        else:
            active.add(tool_name)
        prefs = user.preferences or {}
        # If active equals allowed, store None so executor uses allowed_tools; else store list
        if active == allowed:
            prefs["telegram_tools"] = None
        else:
            prefs["telegram_tools"] = sorted(active)
        user.preferences = prefs
        flag_modified(user, "preferences")
        db.commit()
        db.refresh(user)
        text, keyboard = _build_tools_message_and_keyboard(user, db)
        if keyboard is not None:
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await query.edit_message_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.exception("callback_tools failed: %s", e)
        try:
            await query.edit_message_text("Something went wrong. Try /tools again.")
        except Exception:
            pass
    finally:
        db.close()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages: resolve user via pairing and run agent."""
    if not update.message or not update.message.text:
        return

    telegram_user_id = update.effective_user.id if update.effective_user else None
    if not telegram_user_id:
        return

    db: Session = next(get_db())
    try:
        user = get_user_by_telegram_id(db, telegram_user_id)
        if not user:
            await update.message.reply_text(
                "You are not paired. Go to **Settings → Telegram** in the app to get your pairing code, then send: /start pair YOUR_CODE",
                parse_mode="Markdown",
            )
            return

        conversation = get_current_telegram_conversation(db, user)
        message_text = update.message.text.strip()

        # Typing indicator
        await update.message.chat.send_action("typing")

        prefs = user.preferences or {}
        telegram_tools = prefs.get("telegram_tools")
        telegram_use_mcp = prefs.get("telegram_use_mcp", True)
        telegram_mcp_server_ids = prefs.get("telegram_mcp_server_ids")
        telegram_simple_agent = prefs.get("telegram_simple_agent", False)
        tool_overrides = telegram_tools if telegram_tools is not None else None
        mcp_override = [] if telegram_use_mcp is False else (telegram_mcp_server_ids if telegram_mcp_server_ids is not None else None)
        use_middleware = not telegram_simple_agent

        try:
            final_content = None
            async for event in agent_executor.execute(
                user=user,
                conversation_id=conversation.id,
                message=message_text,
                db=db,
                stream=False,
                selected_tools=None,
                use_deepagent=False,
                file_attachments=None,
                tool_overrides=tool_overrides,
                mcp_server_ids_override=mcp_override,
                use_tool_selector_middleware=use_middleware,
                invocation_source="telegram",
            ):
                if isinstance(event, dict):
                    if event.get("type") == "complete":
                        resp = event.get("response", {})
                        final_content = resp.get("final_answer", "") or ""
                        break
                    if event.get("type") == "error":
                        final_content = event.get("error", "Unknown error")
                        if not final_content.startswith("The AI model"):
                            final_content = f"Error: {final_content}"
                        break

            if final_content is None:
                final_content = "No response generated."

            # Telegram message length limit
            if len(final_content) > 4000:
                final_content = final_content[:3997] + "..."

            await update.message.reply_text(final_content)
        except Exception as e:
            logger.exception("Telegram agent execution failed")
            err = str(e)
            if "Expected dict response" in err and "NoneType" in err:
                await update.message.reply_text(
                    "The AI model returned an unexpected response. Try again or switch to another model in Settings → AI Settings."
                )
            else:
                await update.message.reply_text(f"Sorry, something went wrong: {err[:500]}")
    finally:
        db.close()


def build_application() -> Optional["Application"]:
    """Build and return the Telegram Application if token is configured."""
    if not TELEGRAM_AVAILABLE:
        logger.warning("python-telegram-bot not installed; Telegram bot disabled.")
        return None
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    if not token or not settings.ENABLE_TELEGRAM_BOT:
        return None
    builder = Application.builder().token(token)
    try:
        builder = builder.connect_timeout(30).get_updates_connect_timeout(30)
    except Exception:
        pass
    app = builder.build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("pair", cmd_pair))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("tools", cmd_tools))
    app.add_handler(CallbackQueryHandler(callback_tools, pattern="^tools_"))
    app.add_handler(CommandHandler("newchat", cmd_newchat))
    app.add_handler(CommandHandler("chats", cmd_chats))
    app.add_handler(CallbackQueryHandler(callback_chat_switch, pattern="^chat_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


_telegram_app: Optional["Application"] = None
_telegram_thread: Optional[threading.Thread] = None
_telegram_loop: Optional[asyncio.AbstractEventLoop] = None


def _run_bot_in_thread() -> None:
    """Run the bot in this thread's own event loop (required for run_polling). Retries on connect timeout."""
    global _telegram_app, _telegram_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    _telegram_loop = loop
    max_retries = 5
    backoff_seconds = [10, 20, 40, 60, 60]
    try:
        for attempt in range(max_retries):
            app = build_application()
            if app is None:
                return
            _telegram_app = app
            try:
                loop.run_until_complete(
                    app.run_polling(drop_pending_updates=True, close_loop=True)
                )
                break
            except Exception as e:
                is_timeout = (
                    "Timed out" in str(e)
                    or "ConnectTimeout" in str(e)
                    or "Connection" in type(e).__name__
                )
                _telegram_app = None
                if is_timeout and attempt < max_retries - 1:
                    wait = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                    logger.warning(
                        "Telegram bot connection timed out (attempt %s/%s). Retrying in %ss: %s",
                        attempt + 1, max_retries, wait, e,
                    )
                    time.sleep(wait)
                else:
                    raise
    except Exception as e:
        logger.exception("Telegram bot thread error: %s", e)
    finally:
        _telegram_loop = None
        _telegram_app = None


async def start_telegram_bot() -> None:
    """Start the Telegram bot in a background thread (own event loop). Call from FastAPI startup."""
    global _telegram_thread
    if build_application() is None:
        return
    _telegram_thread = threading.Thread(target=_run_bot_in_thread, daemon=True)
    _telegram_thread.start()
    logger.info("Telegram bot started (polling in background thread).")


async def stop_telegram_bot() -> None:
    """Stop the Telegram bot. Call from FastAPI shutdown."""
    global _telegram_app, _telegram_thread, _telegram_loop
    if _telegram_app is not None:
        try:
            _telegram_app.stop_running()
        except Exception as e:
            logger.debug("Telegram stop_running: %s", e)
    if _telegram_thread is not None:
        _telegram_thread.join(timeout=15.0)
    _telegram_app = None
    _telegram_thread = None
    _telegram_loop = None
    logger.info("Telegram bot stopped.")
