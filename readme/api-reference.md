# API Reference

This is a compact endpoint map for the FastAPI backend. All `/api/*` routes require authentication unless they are auth routes.

## Root, Health, And Metrics

- `GET /` returns app name, version, and running status.
- `GET /health` returns health, uptime, database status, and process metrics.
- `GET /metrics` returns aggregate counts and tool usage where available.

## Auth

Prefix:

```text
/api/auth
```

Endpoints:

- `POST /signup` creates a user.
- `POST /login` authenticates and returns an access token.
- `POST /logout` logs out client-side/token context.
- `GET /me` returns the current user profile.
- `PUT /me` updates the profile.
- `POST /change-password` changes the current user's password.
- `GET /users` lists users for admin users.
- `POST /users` creates a user for admin users.
- `DELETE /users/{user_id}` deletes a user for admin users.

Auth uses JWT bearer tokens and bcrypt password hashing.

## Chat

Prefix:

```text
/api/chat
```

Endpoints:

- `POST /conversations`
- `GET /conversations`
- `GET /conversations/{conversation_id}`
- `GET /conversations/{conversation_id}/steps`
- `PUT /conversations/{conversation_id}`
- `POST /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/upload`
- `POST /conversations/{conversation_id}/stop`
- `DELETE /conversations/{conversation_id}`
- `POST /conversations/{conversation_id}/search`
- `POST /conversations/{conversation_id}/summarize`
- `GET /conversations/{conversation_id}/files`
- `DELETE /conversations/{conversation_id}/files/{message_id}`

The message endpoint supports SSE streaming.

## Tools

Prefix:

```text
/api/tools
```

Endpoints:

- `GET /` lists tools currently allowed for the user.
- `GET /available` lists built-in available tools.
- `GET /{tool_name}` returns details for an allowed tool.
- `POST /execute` directly executes an allowed tool for testing/debugging.
- `GET /permissions/list` lists permission levels.
- `POST /grant-permission` grants or revokes a tool for the current user.

## Custom Tools

Prefix:

```text
/api/custom-tools
```

Endpoints:

- `GET /`
- `POST /`
- `GET /{tool_id}`
- `PUT /{tool_id}`
- `DELETE /{tool_id}`
- `POST /{tool_id}/toggle`
- `POST /generate`

## Settings

Prefix:

```text
/api/settings
```

Endpoints:

- `GET /user`
- `PUT /user`
- `GET /system`
- `GET /paths`
- `PUT /paths`
- `POST /test-ollama`
- `POST /pull-model`
- `GET /api-config`
- `PUT /api-config`
- `GET /api-models/{provider}`
- `GET /exchange`
- `PUT /exchange`
- `POST /exchange/test`
- `GET /telegram`
- `PUT /telegram/config`
- `POST /telegram/pairing-code`

## Documents

Prefix:

```text
/api/documents
```

Endpoints:

- `POST /upload`
- `GET /`
- `DELETE /{document_id}`
- `POST /{document_id}/index`

## Browser Automation

Prefix:

```text
/api/browser-use
```

Endpoints:

- `POST /execute`
- `GET /status`

`/execute` supports SSE streaming.

## MCP

Prefix:

```text
/api/mcp
```

Endpoints:

- `GET /`
- `POST /`
- `GET /{server_id}`
- `PUT /{server_id}`
- `DELETE /{server_id}`
- `POST /{server_id}/test`
- `GET /tools/list`

## Cron Jobs

Prefix:

```text
/api/cron-jobs
```

Endpoints:

- `GET /`
- `POST /`
- `GET /notifications`
- `PATCH /notifications/{notification_id}`
- `GET /{job_id}/runs`
- `GET /{job_id}`
- `PATCH /{job_id}`
- `DELETE /{job_id}`

## API Usage Notes

- Most endpoints require `Authorization: Bearer <token>`.
- Chat and browser automation stream as `text/event-stream` when `stream=true`.
- Conversation, document, tool, MCP, cron, and notification endpoints enforce current-user ownership checks.
- Admin-only routes depend on `is_superuser`.
