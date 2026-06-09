# Agentic-AI

Agentic-AI is a local-first AI agent workspace built with FastAPI, React/Vite, SQLAlchemy, Ollama-friendly model support, vector search, built-in tools, custom tools, MCP server integrations, browser automation, scheduled reminders, Telegram access, Exchange/EWS actions, and a Chrome extension for asking questions about the current webpage.

For the full step-by-step documentation, read [readme/DETAILED_README.md](readme/DETAILED_README.md). The `readme/` directory also contains separate guides for each major capability.

## Core Capabilities

- Multi-user authentication with JWT login, profile settings, admin user management, and per-user tool permissions.
- Chat conversations with streaming responses, saved history, detailed agent steps, stop generation, file attachments, image inputs, and Chrome extension page context.
- LLM provider support for Ollama, OpenAI, DeepSeek, Mistral, and Gemini.
- Local RAG over uploaded user documents with Chroma by default and optional Qdrant.
- Built-in tools for files, documents, web search, webpage scraping, HTTP requests, weather, system info, code analysis, image metadata, network utilities, hashes, database reads, reminders, and Exchange/EWS.
- Runtime custom tools with JSON schemas, permission levels, and AI-assisted generation.
- MCP server connections over HTTP or stdio.
- Cron jobs, reminders, in-app notifications, and optional Telegram delivery.
- Browser automation through `browser-use` with local browsers.
- Docker deployment with optional Ollama, Qdrant, and SearXNG services.

## Quick Start

1. Copy `env.example` to `.env` and set the values for your machine.
2. Start Ollama and pull the configured model, for example:

   ```powershell
   ollama pull qwen3:latest
   ```

3. Install backend dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. Start the backend:

   ```powershell
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

6. Open the frontend, sign up, configure Settings, enable tools, upload documents, and start chatting.

## Detailed Docs

- [Detailed README](readme/DETAILED_README.md)
- [Setup And Running](readme/setup-and-running.md)
- [Architecture](readme/architecture.md)
- [Chat And Agent](readme/chat-and-agent.md)
- [Tools](readme/tools.md)
- [Documents And RAG](readme/documents-and-rag.md)
- [Custom Tools](readme/custom-tools.md)
- [MCP Servers](readme/mcp-servers.md)
- [Cron Jobs, Reminders, And Telegram](readme/cron-jobs-telegram.md)
- [Browser Automation](readme/browser-automation.md)
- [Chrome Extension](readme/chrome-extension.md)
- [Configuration And Settings](readme/configuration-and-settings.md)
- [API Reference](readme/api-reference.md)
- [Deployment And Operations](readme/deployment-and-operations.md)

## License

See [LICENSE](LICENSE).
