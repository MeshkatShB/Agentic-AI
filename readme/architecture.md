# Architecture

Agentic-AI is organized as a FastAPI backend plus a React frontend. Persistent application state is in SQLAlchemy models, long-form searchable text is in a vector store, and runtime services start with the backend.

## Top-Level Layout

```text
backend/              FastAPI app, APIs, auth, models, agent, tools, storage, services
frontend/             React/Vite UI
chrome-extension/     Manifest V3 browser extension
readme/               Detailed documentation
data/                 Optional local data area
user_documents/       Uploaded per-user documents
chroma_db/            Chroma vector database files
logs/                 Backend logs
docker-compose.yml    Container deployment
requirements.txt      Backend Python dependencies
```

## Backend

The FastAPI entry point is `backend/main.py`.

Startup behavior:

1. Loads settings from `backend/config.py`.
2. Creates `logs/app.log`.
3. Creates database tables.
4. Runs migration checks for file attachments, MCP servers, tool counts, Telegram pairing, cron jobs, user notifications, cron runs, cron timezones, and admin flags.
5. Initializes the vector store.
6. Starts the Telegram bot if enabled and configured.
7. Starts the cron job runner.

Shutdown behavior:

1. Stops the Telegram bot.
2. Stops the cron job runner.
3. Clears active agent instances and cancellation tokens.

Main routers:

- `/api/auth` for signup, login, profile, password changes, and admin user management.
- `/api/chat` for conversations, messages, streaming, uploads, steps, files, search, and summaries.
- `/api/tools` for available tools, allowed tools, direct execution, and permission grants.
- `/api/custom-tools` for user-created tools and AI-generated tool code.
- `/api/settings` for user settings, providers, paths, Exchange, Telegram, and Ollama checks.
- `/api/documents` for uploaded document storage and indexing.
- `/api/browser-use` for local browser automation.
- `/api/mcp` for MCP server configurations and tool discovery.
- `/api/cron-jobs` for reminders, scheduled jobs, notifications, and run history.

## Frontend

The frontend is a Vite React app in `frontend/`.

Main routes:

- `/login`
- `/signup`
- `/chat` and `/chat/:conversationId`
- `/documents`
- `/tools`
- `/cron-jobs`
- `/mcp-servers`
- `/browser-use`
- `/add-tool`
- `/edit-tool/:toolId`
- `/settings`

State is held mainly in Zustand stores under `frontend/src/stores/`:

- `authStore.js` handles authentication state.
- `chatStore.jsx` handles chat/conversation state.
- `themeStore.js` handles the UI theme.

The layout sidebar exposes the major capability pages.

## Database

The default database is SQLite through `DATABASE_URL`. Docker examples use `sqlite:///./db/local_agent.db`; local development can use `sqlite:///./local_agent.db`.

Important models:

- `User` stores identity, password hash, profile, preferences, allowed tools, allowed paths, blocked paths, and admin state.
- `Conversation`, `Message`, and `AgentStep` store chat history and detailed tool/reasoning traces.
- `UserDocument` tracks uploaded documents and indexing state.
- `CustomTool` stores user tool code and JSON schema.
- `MCPServer` stores user MCP server configuration.
- `CronJob`, `CronJobRun`, and `UserNotification` store scheduled work and delivery history.
- `TelegramPairing` links a local user to a Telegram user.

## Vector Store

The storage abstraction is in `backend/storage/vector_store.py`.

Supported stores:

- Chroma: default embedded local vector store at `CHROMA_PATH`.
- Qdrant: optional service configured by `QDRANT_URL`.

Collections include:

- `conversations`
- `documents`
- `tools`
- `user_documents_{user_id}` for uploaded user document retrieval.

Embedding settings are controlled by `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `EMBEDDING_DEVICE`, `CHUNK_SIZE`, and `CHUNK_OVERLAP`.

## Agent Flow

The agent stack is under `backend/agent/`.

1. The chat API receives a message.
2. Attachments and webpage context are folded into the user message.
3. `AgentExecutor` saves the user message, loads user preferences, registers custom tools, resolves selected tools, adds Exchange tools if configured, and gathers message history.
4. `Agent` creates a LangChain agent with the configured model and selected tools.
5. MCP tools are loaded from enabled MCP servers and appended to the LangChain tool list.
6. The response streams as server-sent events, including tokens, steps, completion, title updates, errors, or cancellation.
7. Final assistant output and agent steps are persisted.
8. The final answer is saved to vector memory when supported.

## Runtime Services

- Cron runner: background thread that executes due `CronJob` rows.
- Telegram bot: optional polling bot created from `TELEGRAM_BOT_TOKEN`.
- MCP service: caches MultiServerMCP clients per user.
- Browser-use endpoint: creates local browser sessions on demand.

## Privacy Model

The default design is local-first:

- SQLite, Chroma, uploaded documents, logs, and conversations stay on the host unless configured otherwise.
- Ollama is the default LLM provider.
- Network-capable tools must be enabled for the user.
- External API providers, web search, Exchange, Telegram, MCP servers, and browser automation are opt-in configuration paths.
