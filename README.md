# Local-First AI Agent Application

A privacy-preserving, local-first AI agent that can search, reason, plan, and execute tools with user consent. Built with FastAPI, React, Ollama, and vector storage.

## Features

- 🔒 **100% Local-First**: All processing happens on your machine
- 🤖 **Ollama Integration**: Uses Qwen3 model with tool calling support
- 👤 **Multi-User Support**: Per-user accounts with customizable settings
- 🔍 **Smart Search**: Local file search and web search (with permission)
- 🧠 **Memory & Context**: Vector storage for conversation history
- 🛡️ **Privacy First**: No telemetry, permission gates for all tools
- 🎨 **Beautiful UI**: Modern glassmorphism design with step-by-step visualization

## Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama installed and running
- Docker (optional, for Qdrant)

## Quick Start

### 1. Install Ollama and Pull Qwen3

```bash
# Install Ollama (Windows)
# Download from: https://ollama.com/download

# Pull Qwen3 model
ollama pull qwen3:latest

# Verify Ollama is running
curl http://127.0.0.1:11434/api/tags
```

### 2. Set Up Backend

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python backend/init_db.py

# Start the backend server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Set Up Vector Storage

#### Option A: Chroma (Embedded - Recommended for simplicity)

```bash
# Chroma is installed with pip requirements
# No additional setup needed
```

#### Option B: Qdrant (Local Service)

```bash
# Run Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant
```

### 4. Set Up Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Access the Application

Open http://localhost:5173 in your browser

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Backend
SECRET_KEY=your-secret-key-here-change-in-production
DATABASE_URL=sqlite:///./local_agent.db
OLLAMA_BASE_URL=http://127.0.0.1:11434
DEFAULT_MODEL=qwen3:latest

# Vector Storage
VECTOR_STORE=chroma  # or "qdrant"
CHROMA_PATH=./chroma_db
QDRANT_URL=http://localhost:6333

# Security
ALLOWED_FILE_PATHS=/home/user/documents,/home/user/downloads
BLOCKED_FILE_PATHS=/etc,/system32
MAX_STEPS_PER_REQUEST=10
MAX_TOKENS_PER_STEP=2000

# Optional: Web Search (requires user permission)
SEARXNG_URL=http://localhost:8888  # Optional local search instance
```

### User Settings

Each user can customize:

- Default model selection
- Temperature and other LLM parameters
- Allowed tools
- File access paths
- UI theme
- Step limits and timeouts

## Architecture

```
local-ai-agent/
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── auth/                   # Authentication module
│   ├── models/                 # Database models
│   ├── llm/                    # Ollama client & adapters
│   ├── tools/                  # Tool registry & implementations
│   ├── storage/                # Vector storage abstraction
│   ├── agent/                  # ReAct loop implementation
│   └── api/                    # API endpoints
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API services
│   │   ├── stores/             # State management
│   │   └── styles/             # Tailwind styles
│   └── package.json
├── tests/                      # Test suite
├── docker-compose.yml          # Optional containerization
└── requirements.txt            # Python dependencies
```

## Tool Registry

Available tools (all require user permission):

| Tool                 | Description                    | Permission Level |
| -------------------- | ------------------------------ | ---------------- |
| `search_local_files` | Search indexed local documents | Read Files       |
| `read_file`          | Read specific file content     | Read Files       |
| `parse_document`     | Extract text from PDF/DOCX/etc | Read Files       |
| `web_search`         | Search the web (when allowed)  | Network Access   |
| `calculator`         | Perform calculations           | Safe             |
| `query_database`     | Read from local SQLite         | Read Database    |
| `write_database`     | Write to local SQLite          | Write Database   |

## Security & Privacy

- **No Telemetry**: Zero external tracking or analytics
- **Local Storage**: All data stored locally in SQLite and vector DB
- **Permission Gates**: Every tool requires explicit user consent
- **Sandboxed Access**: Configurable file path restrictions
- **Session Security**: JWT tokens with secure password hashing
- **Offline Mode**: Network toggle to block all external connections

## Development

### Running Tests

```bash
# Backend tests
pytest tests/backend/

# Frontend tests
cd frontend && npm test

# End-to-end tests
pytest tests/e2e/
```

### Adding New Tools

1. Create tool in `backend/tools/registry/`
2. Define schema and permission requirements
3. Register in tool registry
4. Add UI permission dialog component
5. Test with permission gates

### Switching Vector Stores

The app supports both Chroma and Qdrant. To switch:

1. Update `VECTOR_STORE` in `.env`
2. Ensure the chosen store is running
3. Restart the backend

## Troubleshooting

### Ollama Connection Issues

```bash
# Check Ollama is running
curl http://127.0.0.1:11434/api/tags

# Verify model is available
ollama list
```

### Vector Store Issues

```bash
# For Chroma
python -c "import chromadb; print(chromadb.__version__)"

# For Qdrant
curl http://localhost:6333/collections
```

### Permission Denied Errors

- Check `ALLOWED_FILE_PATHS` in `.env`
- Ensure user has tool permissions in settings
- Verify file system permissions

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Support

For issues and questions, please use the GitHub issue tracker.
