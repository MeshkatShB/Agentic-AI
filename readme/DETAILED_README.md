# Agentic-AI Detailed README

This directory is the detailed documentation set for the Agentic-AI application. Start here when you want to understand what the app can do, then open the capability-specific files for setup and step-by-step usage.

Agentic-AI is a local-first AI agent workspace. It combines a FastAPI backend, a React/Vite frontend, local or API-hosted language models, vector search over user documents, built-in tools, user-created tools, MCP server integrations, browser automation, scheduled reminders, Telegram access, Exchange/EWS actions, and a Chrome extension that sends webpage context into chat.

## Documentation Map

- [Setup And Running](setup-and-running.md) - local development, Docker, Ollama, frontend/backend startup, and health checks.
- [Architecture](architecture.md) - backend, frontend, database, vector stores, startup services, and request flow.
- [Chat And Agent](chat-and-agent.md) - conversations, streaming, tools, file attachments, image inputs, page context, memory, and DeepAgent fallback.
- [Tools](tools.md) - every built-in tool family, permissions, how to enable tools, direct tool execution, and Exchange tools.
- [Documents And RAG](documents-and-rag.md) - upload, parse, index, search, reindex, and document limits.
- [Custom Tools](custom-tools.md) - create tools manually or with AI, allowed imports, schema rules, runtime registration, and safety model.
- [MCP Servers](mcp-servers.md) - HTTP and stdio MCP server configuration, connection tests, tool loading, and test server usage.
- [Cron Jobs, Reminders, And Telegram](cron-jobs-telegram.md) - scheduling from chat/UI, recurring jobs, notifications, Telegram pairing, and Telegram tool scope.
- [Browser Automation](browser-automation.md) - browser-use execution with local browsers and user-selected LLM providers.
- [Chrome Extension](chrome-extension.md) - install, configure, authenticate, send page context, and troubleshoot extension use.
- [Configuration And Settings](configuration-and-settings.md) - environment variables, per-user settings, LLM providers, paths, Exchange, Telegram, and CORS.
- [API Reference](api-reference.md) - main FastAPI routers and endpoint groups.
- [Deployment And Operations](deployment-and-operations.md) - Docker deployment, logs, monitoring scripts, migrations, troubleshooting, and known limitations.

## Capability Summary

1. Authentication and multi-user workspaces with JWT login, signup, profile updates, admin-only user management, and per-user preferences.
2. Chat conversations with streaming responses, saved message history, auto-generated titles, stop generation, conversation search, summaries, file attachments, and detailed agent-step traces.
3. Multi-provider LLM support through Ollama, OpenAI, DeepSeek, Mistral, and Gemini, configured globally through environment variables or per user in Settings.
4. Local vector memory using Chroma by default, with optional Qdrant support, per-user document collections, configurable embedding models, and semantic retrieval.
5. Built-in tools for local file search, file reads, document parsing, web search, webpage scraping, HTTP requests, weather, system inspection, code analysis, image metadata, network utilities, hashes, database reads, scheduling, and optional Exchange/EWS email/calendar/task actions.
6. User-created custom tools stored in SQLite, registered at runtime, with JSON schemas, permission levels, AI-assisted generation, and a restricted import allowlist.
7. MCP server integrations for user-configured HTTP or stdio servers, connection testing, tool discovery, and automatic agent tool loading.
8. Scheduled jobs and reminders that can be created from chat or UI, run in the backend background scheduler, create in-app notifications, and optionally deliver Telegram reminders.
9. Telegram bot access with pairing codes, a dedicated Telegram conversation, tool selection, optional MCP server selection, and chat command support.
10. Browser automation powered by `browser-use`, using local browsers only and the user's configured LLM provider.
11. Chrome extension support for extracting the current webpage and asking the local agent questions about it.
12. Docker deployment with backend, frontend, optional Ollama, optional Qdrant, and optional SearxNG services.

## Most Common Path

1. Copy `env.example` to `.env` and set at least `SECRET_KEY`, `DATABASE_URL`, `OLLAMA_BASE_URL`, `DEFAULT_MODEL`, `VECTOR_STORE`, and CORS values.
2. Start Ollama and pull the configured model, for example `qwen3:latest`.
3. Install Python dependencies from `requirements.txt`.
4. Initialize or migrate the database by running the backend; `backend/main.py` creates tables and runs migration checks on startup.
5. Start the backend on port `8000` for local development, or use Docker where the backend is exposed as port `3333`.
6. Install frontend dependencies under `frontend/` and run Vite.
7. Create a user, sign in, choose tools in the Tools page, upload documents in Documents, and ask the agent to use the enabled capabilities.

For full commands and platform notes, read [Setup And Running](setup-and-running.md).
