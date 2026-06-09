# Setup And Running

This guide covers the normal local development path and the Docker path.

## Prerequisites

- Python 3.11 or newer.
- Node.js 18 or newer.
- Ollama if you want the default local model flow.
- Docker Desktop if you want containerized deployment, Qdrant, SearxNG, or Docker-hosted Ollama.
- Enough disk space for embedding models, local vector data, uploaded user documents, logs, and optional Ollama models.

## Local Development

1. Create a `.env` file from the example:

   ```powershell
   Copy-Item env.example .env
   ```

2. Edit `.env`.

   For local development, these values are usually the important ones:

   ```env
   SECRET_KEY=replace-with-a-long-random-secret
   DATABASE_URL=sqlite:///./local_agent.db
   OLLAMA_BASE_URL=http://127.0.0.1:11434
   DEFAULT_MODEL=qwen3:latest
   VECTOR_STORE=chroma
   CHROMA_PATH=./chroma_db
   CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080
   ```

3. Start Ollama and pull the model:

   ```powershell
   ollama pull qwen3:latest
   ollama list
   ```

4. Create and activate a Python environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

5. Install backend dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

6. Initialize the database if needed:

   ```powershell
   python backend/init_db.py
   ```

   The backend also calls `Base.metadata.create_all()` and runs migration checks on startup, so an existing database is updated for the tables and columns represented by the migration scripts.

7. Start the backend:

   ```powershell
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

8. In another terminal, install and start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

9. Open the Vite URL, normally `http://localhost:5173`.

10. Create an account through Signup, sign in, then configure tools and settings.

## Health Checks

Use these backend endpoints:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/metrics
```

`/health` reports app status, uptime, database connectivity, and basic process metrics when `psutil` is available. `/metrics` reports user, conversation, message, and tool-step counts where tables exist.

## Docker

The Docker deployment exposes:

- Backend API on host port `3333`.
- Frontend on host port `8080`.
- Optional Ollama on `11434` with the `ollama-docker` profile.
- Optional Qdrant on `6333` with the `qdrant` profile.
- Optional SearxNG on `8888` with the `search` profile.

Basic Docker startup:

```powershell
docker compose up --build
```

With optional services:

```powershell
docker compose --profile qdrant --profile search up --build
```

With Docker-hosted Ollama:

```powershell
docker compose --profile ollama-docker up --build
```

For Docker using host Ollama, set:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

For Docker using the Ollama service, set:

```env
OLLAMA_BASE_URL=http://ollama:11434
```

## Useful Startup Scripts

- `start.bat` and `start.sh` are local convenience scripts.
- `docker-start.bat` and `docker-start.sh` are Docker convenience scripts.
- `docker-entrypoint.sh` prepares backend container startup.

## First Login Checklist

1. Open the frontend.
2. Sign up or log in.
3. Go to Settings and confirm the LLM provider and model.
4. Go to Tools and enable the tools the agent may use.
5. Upload documents in Documents if you want local RAG.
6. Add MCP servers in MCP Servers if you want external MCP tools.
7. Configure Telegram or Exchange only if you need those integrations.

## Common Problems

- Ollama connection fails: verify `OLLAMA_BASE_URL` and run `ollama list`.
- Frontend cannot reach backend: check Vite proxy/base URL configuration and CORS.
- Chroma embedding dimension errors: the Chroma store attempts to reset known collections when the embedding model changes, but already indexed data may need reindexing.
- Web search returns disabled: set `ENABLE_WEB_SEARCH=true` and optionally configure SearxNG.
- Browser automation fails: ensure the `browser-use` package is installed and a local browser/Chromium is available.
