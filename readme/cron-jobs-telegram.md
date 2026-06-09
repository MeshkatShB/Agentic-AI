# Cron Jobs, Reminders, And Telegram

The app can schedule reminders from chat, create scheduled jobs from the UI/API, store run history, create in-app notifications, and optionally deliver reminders through Telegram.

## Scheduling From Chat

The built-in `schedule_job` tool creates jobs when the user asks for reminders or scheduled tasks.

Example prompts:

```text
Remind me tomorrow at 9am to call Sara.
Remind me every weekday at 7am to check the report.
Schedule a reminder for 2026-06-12 18:30 to submit the form.
```

The agent system prompt explicitly says reminder requests must call `schedule_job`; a text-only promise does not create a job.

## Scheduling From UI/API

Endpoint:

```text
POST /api/cron-jobs/
```

Fields:

- `title`
- `job_type`, default `reminder`
- `next_run_at`
- `cron_expression`, optional recurring schedule
- `schedule_timezone`, optional IANA timezone
- `payload`, optional extra data such as reminder body
- `source`, default `ui`

## Job Lifecycle

Job statuses include:

- `scheduled`
- `running`
- `completed`
- `failed`
- `cancelled`

For recurring jobs with a cron expression, the runner computes the next run instead of marking the job completed after a successful run.

## Background Runner

`backend.services.cron_job_runner` starts on backend startup.

It:

1. Finds due scheduled jobs.
2. Marks a job running.
3. Creates a `CronJobRun` record.
4. Creates in-app `UserNotification` rows for reminders.
5. Sends Telegram messages when the job source or pairing supports delivery.
6. Marks one-shot jobs completed or failed.
7. Reschedules recurring jobs.

## Cron Job API

- `GET /api/cron-jobs/` lists jobs with optional status and job type filters.
- `POST /api/cron-jobs/` creates a job.
- `GET /api/cron-jobs/{job_id}` fetches one job.
- `PATCH /api/cron-jobs/{job_id}` updates scheduled jobs.
- `DELETE /api/cron-jobs/{job_id}` deletes a job.
- `GET /api/cron-jobs/{job_id}/runs` lists run history.
- `GET /api/cron-jobs/notifications` lists in-app notifications.
- `PATCH /api/cron-jobs/notifications/{notification_id}` marks a notification as read.

## Telegram Setup

Telegram is optional.

Environment:

```env
ENABLE_TELEGRAM_BOT=true
TELEGRAM_BOT_TOKEN=your-bot-token
```

Create the bot with BotFather, set the token, and restart the backend.

## Pairing A User

1. Sign in to the web UI.
2. Open Settings.
3. Open Telegram settings.
4. Copy or regenerate the pairing code.
5. In Telegram, start the bot.
6. Use the bot's pair command with the pairing code.
7. Confirm Settings shows the Telegram account as paired.

## Telegram Commands

The Telegram service includes handlers for:

- `/start`
- `/pair`
- `/status`
- `/help`
- `/newchat`
- `/chats`
- `/tools`

It also handles normal messages by passing them into the agent executor.

## Telegram Conversation Model

Telegram messages use a dedicated conversation titled `Telegram` unless the user switches conversation context with bot controls.

Telegram-specific preferences can define:

- `telegram_tools`
- `telegram_use_mcp`
- `telegram_mcp_server_ids`
- `telegram_simple_agent`

This lets Telegram have a smaller or different tool/MCP surface than the web UI.

## Telegram Settings API

- `GET /api/settings/telegram` returns bot status, pairing state, selected tools, MCP server options, and pairing code.
- `PUT /api/settings/telegram/config` updates Telegram tool and MCP choices.
- `POST /api/settings/telegram/pairing-code` regenerates the code and unpairs any existing Telegram user.

## Timezones

User settings include `timezone`. The scheduler uses it when parsing reminder strings such as `tomorrow at 9am`. Cron expressions may also store `schedule_timezone`.

Use IANA names such as:

```text
Asia/Tehran
America/New_York
Europe/London
```
