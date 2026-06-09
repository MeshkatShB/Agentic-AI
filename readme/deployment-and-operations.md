# Deployment And Operations

This guide covers deployment, logs, monitoring, migrations, backups, and known operational limits.

## Docker Services

`docker-compose.yml` defines:

- `backend`: FastAPI backend, exposed as `3333:3333`.
- `frontend`: built static frontend served by Nginx, exposed as `8080:80`.
- `ollama`: optional Ollama service behind profile `ollama-docker`.
- `qdrant`: optional Qdrant service behind profile `qdrant`.
- `searxng`: optional private search service behind profile `search`.

Persistent mounts:

- `./db:/app/db`
- `./chroma_db:/app/chroma_db`
- `./user_documents:/app/user_documents`
- `./data:/app/data`
- `./logs:/app/logs`
- `./.env:/app/.env:ro`

## Docker Startup

Basic:

```powershell
docker compose up --build
```

With Qdrant and SearXNG:

```powershell
docker compose --profile qdrant --profile search up --build
```

With Docker-hosted Ollama:

```powershell
docker compose --profile ollama-docker up --build
```

## Ports

Local development commonly uses:

- Backend: `8000`
- Frontend: `5173`
- Ollama: `11434`
- Qdrant: `6333`
- SearXNG: `8888`

Docker compose exposes:

- Backend: `3333`
- Frontend: `8080`
- Optional Ollama: `11434`
- Optional Qdrant: `6333`
- Optional SearXNG: `8888`

## Logs

Backend logs are written to:

```text
logs/app.log
```

The backend also logs to console.

Useful scripts:

- `analyze_logs.py` for log analysis.
- `monitor_dashboard.py` for a local monitoring dashboard.

## Health And Metrics

Check:

```text
GET /health
GET /metrics
```

Docker backend healthcheck calls:

```text
http://localhost:3333/health
```

Frontend healthcheck calls:

```text
http://localhost:80
```

## Database Migrations

The backend currently uses lightweight migration scripts in `backend/migrations/`. On startup, `backend/main.py` attempts migrations for:

- File attachments on messages.
- MCP servers table.
- Last MCP tool count.
- Telegram pairing table.
- Cron jobs table.
- User notifications table.
- Cron timezone.
- Cron job runs table.
- User `is_superuser`.

It is safe for these checks to log warnings when a column or table already exists.

## Backups

For a local or Docker SQLite/Chroma deployment, back up:

- `local_agent.db` or `db/local_agent.db`
- `chroma_db/`
- `user_documents/`
- `.env`
- any external vector database volumes such as `qdrant_data`

For Ollama, model storage is outside this app unless using the Docker volume `ollama_data`.

## Security Checklist

1. Replace `SECRET_KEY`.
2. Restrict CORS for non-development deployments.
3. Review `ALLOWED_FILE_PATHS` and `BLOCKED_FILE_PATHS`.
4. Enable only necessary tools for each user.
5. Avoid granting custom tool creation to untrusted users.
6. Use HTTPS and a reverse proxy for remote access.
7. Treat Exchange, Telegram, and external LLM keys as secrets.
8. Review logs before sharing them because they may include tool errors or contextual text.

## Known Limitations

- Document vector chunk deletion is not fully implemented when deleting a document.
- `custom_api` is a template and does not point to a real service.
- `get_weather` needs a real OpenWeatherMap-compatible key for dependable use.
- Browser automation provider handling does not include a dedicated DeepSeek branch.
- Some README files that predate this documentation contain encoding artifacts in decorative characters; this detailed documentation uses ASCII.
- The project includes `package-lock.json` at the root, but the real frontend package is in `frontend/`.

## Troubleshooting

- Backend starts but frontend cannot connect: check frontend proxy/base URL, backend port, and CORS.
- Docker backend cannot reach host Ollama: set `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- Qdrant errors: confirm the profile is running and `VECTOR_STORE=qdrant`.
- SearXNG search errors: confirm profile is running and `ENABLE_WEB_SEARCH=true`.
- Telegram does not respond: confirm `ENABLE_TELEGRAM_BOT=true`, token validity, backend restart, and user pairing.
- MCP tools missing: test the MCP server in the MCP Servers page and confirm it is active/enabled.
