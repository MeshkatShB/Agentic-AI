# Configuration And Settings

Configuration is split between environment variables in `.env` and per-user settings stored in the database.

## Environment Settings

Settings are defined in `backend/config.py` and loaded with Pydantic Settings from `.env`.

### App And Security

```env
APP_NAME=Local AI Agent
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=replace-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

Change `SECRET_KEY` before any shared or production-like deployment.

### Database

```env
DATABASE_URL=sqlite:///./local_agent.db
```

Docker examples use:

```env
DATABASE_URL=sqlite:///./db/local_agent.db
```

`psycopg2-binary` is included for optional PostgreSQL work, but the current compose file uses SQLite.

### Ollama

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_MODEL=qwen3:latest
MODEL_TEMPERATURE=0.7
MODEL_MAX_TOKENS=2000
```

For Docker reaching host Ollama:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

### External LLM Providers

Optional global keys:

```env
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
MISTRAL_API_KEY=
GEMINI_API_KEY=
```

Users can also configure provider keys and models in Settings. User config takes precedence over environment fallback.

Supported provider values:

- `ollama`
- `openai`
- `deepseek`
- `mistral`
- `gemini`

### Vector Store

```env
VECTOR_STORE=chroma
CHROMA_PATH=./chroma_db
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=agent_memory
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
EMBEDDING_DIMENSION=1024
EMBEDDING_DEVICE=auto
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_RETRIEVAL_RESULTS=10
```

`EMBEDDING_DEVICE` can be `auto`, `cpu`, `cuda`, or `mps`.

### File Access

```env
ALLOWED_FILE_PATHS=./data,./documents
BLOCKED_FILE_PATHS=/etc,/system32,/Windows/System32
MAX_FILE_SIZE_MB=100
```

`read_file` and `parse_document` enforce the path allow/block rules.

### Agent

```env
MAX_STEPS_PER_REQUEST=10
MAX_TOKENS_PER_STEP=2000
STEP_TIMEOUT_SECONDS=30
REQUIRE_TOOL_CONFIRMATION=true
```

Some legacy values remain in settings (`USE_LANGGRAPH`, `REASONING_MODE`, `AGENT_TYPE`) but the current agent flow uses the base LangChain agent.

### Web Search

```env
ENABLE_WEB_SEARCH=true
SEARXNG_URL=http://localhost:8888/
WEB_SEARCH_TIMEOUT=10
```

If SearXNG is unavailable, `web_search` can fall back to DuckDuckGo.

### Telegram

```env
ENABLE_TELEGRAM_BOT=false
TELEGRAM_BOT_TOKEN=
```

### CORS

```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080
```

`*` is supported but less restrictive. Chrome extension origins are handled with a regex in `backend/main.py` when not allowing all origins.

## Per-User Settings

Endpoint group:

```text
/api/settings
```

Users can configure:

- Theme.
- Default model.
- Embedding model.
- Temperature.
- Max steps.
- Max tokens.
- Tool confirmation preference.
- Timezone.
- File access paths.
- API provider and model settings.
- Exchange settings.
- Telegram settings.

When user settings change, the backend clears the user's active agent so the next request uses fresh settings.

## API Provider Settings

API config fields include:

- `llm_provider`
- OpenAI key, endpoint, model.
- DeepSeek key, endpoint, model.
- Mistral key, endpoint, model.
- Gemini key, endpoint, model.

Endpoints:

- `GET /api/settings/api-config`
- `PUT /api/settings/api-config`
- `GET /api/settings/api-models/{provider}`

Returned API keys may be masked after update.

## Ollama Settings

Endpoints:

- `GET /api/settings/system` lists basic app info and Ollama models.
- `POST /api/settings/test-ollama` checks connectivity.
- `POST /api/settings/pull-model` pulls a model and requires admin/superuser status.

## Path Settings

Endpoints:

- `GET /api/settings/paths`
- `PUT /api/settings/paths`

System paths from `.env` are combined with user paths.

## Exchange Settings

Endpoints:

- `GET /api/settings/exchange`
- `PUT /api/settings/exchange`
- `POST /api/settings/exchange/test`

Fields:

- `enabled`
- `server`
- `email`
- `username`
- `password`

Passwords are masked in responses.

## Telegram Settings

Endpoints:

- `GET /api/settings/telegram`
- `PUT /api/settings/telegram/config`
- `POST /api/settings/telegram/pairing-code`

Settings include pairing status, pairing code, Telegram-specific tool list, MCP usage, selected MCP servers, and simple-agent preference.
