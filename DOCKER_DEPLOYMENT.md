# Docker Deployment Guide

This guide explains how to deploy the Local AI Agent application using Docker.

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+
- At least 4GB of available RAM
- (Optional) NVIDIA Docker runtime for GPU support with Ollama

## Quick Start

1. **Clone the repository** (if not already done):

   ```bash
   git clone <repository-url>
   cd Agentic-AI
   ```

2. **Create environment file**:

   ```bash
   cp env.example .env
   ```

   Edit `.env` and configure your settings (especially `SECRET_KEY` for production).

3. **Start all services**:

   ```bash
   docker-compose up -d
   ```

   **Note**: `docker-compose up -d` will automatically build images if they don't exist. However, if you've made code changes and want to rebuild, use:

   ```bash
   docker-compose up -d --build
   ```

   Or build first, then start:

   ```bash
   docker-compose build
   docker-compose up -d
   ```

4. **Access the application**:

   - Frontend: http://localhost:8080
   - Backend API: http://localhost:3333
   - API Documentation: http://localhost:3333/docs
   - Ollama: http://localhost:11434 (if using Docker Ollama service)

5. **Check logs**:
   ```bash
   docker-compose logs -f
   ```

## Services

### Main Services

- **backend**: FastAPI application (port 3333)
- **frontend**: React/Vite application served via Nginx (port 8080)
- **ollama**: LLM service (port 11434) - **Optional** (can use host's Ollama instead)

### Optional Services

- **qdrant**: Vector database (port 6333) - Use with profile `qdrant`
- **searxng**: Private web search (port 8888) - Use with profile `search`

## Configuration

### Using Host's Ollama vs Docker Ollama

**Option 1: Use Host's Ollama (Recommended if Ollama is already running)**

If you have Ollama running on your host machine (outside Docker):

1. **Set in `.env` file**:

   ```
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```

2. **Don't start Docker Ollama service** - it's already configured to use a profile, so it won't start by default.

**Option 2: Use Docker Ollama Service**

If you want to run Ollama in Docker:

1. **Set in `.env` file**:

   ```
   OLLAMA_BASE_URL=http://ollama:11434
   ```

2. **Start with Ollama profile**:

   ```bash
   docker-compose --profile ollama-docker up -d
   ```

3. **Or uncomment `depends_on: ollama` in docker-compose.yml** and remove the profile from the ollama service.

**Note**: If you get a port conflict error (port 11434 already in use), you're likely using Option 1. Make sure your `.env` has `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

### Environment Variables

Edit the `.env` file to configure:

- `SECRET_KEY`: Secret key for JWT tokens (change in production!)
- `DATABASE_URL`: Database connection string (default: SQLite)
- `OLLAMA_BASE_URL`: Ollama service URL (default: http://host.docker.internal:11434)
- `DEFAULT_MODEL`: Default LLM model (default: qwen3:latest)
- `VECTOR_STORE`: Vector store type - `chroma` or `qdrant` (default: chroma)
- `EMBEDDING_DEVICE`: Device for embeddings - `auto`, `cpu`, `cuda`, `mps` (default: auto, use `cpu` for Docker without GPU)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)

### Using PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

1. Add PostgreSQL service to `docker-compose.yml`:

   ```yaml
   postgres:
     image: postgres:15-alpine
     environment:
       POSTGRES_DB: local_agent
       POSTGRES_USER: agent
       POSTGRES_PASSWORD: your_password
     volumes:
       - postgres_data:/var/lib/postgresql/data
   ```

2. Update `.env`:

   ```
   DATABASE_URL=postgresql://agent:your_password@postgres:5432/local_agent
   ```

3. Install psycopg2 in backend (add to requirements.txt):
   ```
   psycopg2-binary==2.9.9
   ```

### Using Qdrant (Optional)

To use Qdrant instead of ChromaDB:

1. Start Qdrant service:

   ```bash
   docker-compose --profile qdrant up -d qdrant
   ```

2. Update `.env`:
   ```
   VECTOR_STORE=qdrant
   QDRANT_URL=http://qdrant:6333
   ```

### Using SearxNG (Optional)

To enable private web search:

1. Start SearxNG service:

   ```bash
   docker-compose --profile search up -d searxng
   ```

2. Update `.env`:
   ```
   ENABLE_WEB_SEARCH=true
   SEARXNG_URL=http://searxng:8080
   ```

## GPU Support for Ollama

To enable GPU support for Ollama (requires NVIDIA Docker runtime):

1. Install NVIDIA Docker runtime:

   ```bash
   # Follow instructions at: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
   ```

2. Uncomment GPU configuration in `docker-compose.yml` under the `ollama` service:
   ```yaml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             count: 1
             capabilities: [gpu]
   ```

## Building Images

### When do you need to build?

**First time setup**: `docker-compose up -d` will automatically build images if they don't exist, so you don't need to run `build` separately.

**After code changes**: If you've modified the code and want to rebuild:

- Use `docker-compose up -d --build` to rebuild and start
- Or build first, then start:
  ```bash
  docker-compose build
  docker-compose up -d
  ```

**Note**: If images already exist, `docker-compose up -d` will NOT rebuild them automatically, even if source code changed. You must use `--build` flag or run `build` first.

### Build all images:

```bash
docker-compose build
```

### Build specific service:

```bash
docker-compose build backend
docker-compose build frontend
```

### Force rebuild (no cache):

```bash
docker-compose build --no-cache
```

## Managing Services

### Start services:

```bash
docker-compose up -d
```

### Stop services:

```bash
docker-compose down
```

### Stop and remove volumes (⚠️ deletes data):

```bash
docker-compose down -v
```

### View logs:

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart a service:

```bash
docker-compose restart backend
```

### Execute commands in container:

```bash
# Backend shell
docker-compose exec backend bash

# Run database migration
docker-compose exec backend python backend/init_db.py
```

## Data Persistence

The following directories are mounted as volumes to persist data:

- `./db` - SQLite database directory (contains `local_agent.db` if using SQLite)
- `./chroma_db` - ChromaDB vector store data
- `./user_documents` - User uploaded documents
- `./data` - Application data files
- `./logs` - Application logs
- `ollama_data` - Ollama models (Docker volume)
- `qdrant_data` - Qdrant data (Docker volume, if using Qdrant)

## Initial Setup

After first deployment:

1. **Pull Ollama model**:

   - **If using Docker Ollama service**:

     ```bash
     docker-compose exec ollama ollama pull qwen3:latest
     ```

   - **If using host's Ollama**:
     ```bash
     ollama pull qwen3:latest
     ```

2. **Create admin user** (if database was initialized):
   - Default credentials: `admin / admin123`
   - Change password immediately after first login!

## Troubleshooting

### CUDA/GPU Error: "Found no NVIDIA driver"

If you see `RuntimeError: Found no NVIDIA driver on your system`:

**This means the embedding model is trying to use GPU but no GPU is available in Docker.**

**Solution**: Set `EMBEDDING_DEVICE=cpu` in your `.env` file:

```bash
# In .env file
EMBEDDING_DEVICE=cpu
```

Or it will automatically use CPU if `EMBEDDING_DEVICE=auto` (the new default).

**For GPU support** (if you have NVIDIA GPU):

1. Install NVIDIA Docker runtime
2. Uncomment GPU configuration in `docker-compose.yml` for the backend service
3. Set `EMBEDDING_DEVICE=cuda` in `.env`

**Note**: The default is now `auto` which will automatically detect and use CPU if no GPU is available.

### Build fails with JSON decode error

If you see `json.decoder.JSONDecodeError` during `pip install`:

1. **This is usually a transient PyPI issue**. Try:

   ```bash
   docker-compose build --no-cache backend
   ```

2. **If it persists**, try installing packages in smaller groups:

   - Edit `Dockerfile.backend` temporarily to install core packages first
   - Or use a different PyPI mirror by adding to Dockerfile:
     ```dockerfile
     RUN pip config set global.index-url https://pypi.org/simple
     ```

3. **Check your network connection** - PyPI might be temporarily unavailable

4. **Try building at a different time** - PyPI issues are often temporary

### SQLite "unable to open database file" error

If you see `sqlite3.OperationalError: unable to open database file`:

1. **Ensure the db directory exists on the host**:

   ```bash
   mkdir -p db
   chmod 755 db
   ```

2. **Check volume mount permissions**:

   ```bash
   # On Linux/Mac, ensure the directory is writable
   chmod -R 755 db

   # On Windows, ensure Docker Desktop has access to the directory
   ```

3. **Verify the database path in .env**:

   ```
   DATABASE_URL=sqlite:///./db/local_agent.db
   ```

4. **If using existing database**, migrate it to the db directory:

   ```bash
   # If you have an existing local_agent.db in the project root
   mkdir -p db
   if [ -f local_agent.db ]; then
       cp local_agent.db db/local_agent.db
       chmod 664 db/local_agent.db
       echo "✅ Database migrated to db/local_agent.db"
   fi
   ```

5. **Rebuild and restart**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

### Backend won't start

1. Check logs:

   ```bash
   docker-compose logs backend
   ```

2. Verify environment variables:

   ```bash
   docker-compose exec backend env | grep -E "DATABASE_URL|OLLAMA_BASE_URL"
   ```

3. Check database connection:
   ```bash
   docker-compose exec backend python -c "from backend.models import engine; print(engine)"
   ```

### Frontend shows connection errors

1. Verify backend is running:

   ```bash
   docker-compose ps
   curl http://localhost:3333/health
   ```

2. Check CORS settings in `.env`:

   ```
   # For local access
   CORS_ORIGINS=http://localhost:8080,http://localhost:3333

   # For Chrome extension access from different machines, use:
   CORS_ORIGINS=*
   ```

### Port 80 already in use (Caddy or other web server)

If you see Caddy's welcome page or another web server when accessing `http://localhost`:

**This means port 80 is already in use by another service (like Caddy).**

**Solution**: The frontend is now configured to use port **8080** instead of 80. Access your application at:

- **Frontend**: http://localhost:8080
- **Backend API**: http://localhost:3333

If you want to use port 80, you'll need to:

1. Stop the service using port 80 (e.g., Caddy)
2. Change the frontend port mapping in `docker-compose.yml` back to `"80:80"`

### Port 11434 already in use

If you see `bind: Only one usage of each socket address (protocol/network address/port) is normally permitted`:

**This means Ollama is already running on your host machine.** You have two options:

**Option 1: Use Host's Ollama (Recommended)**

1. Update your `.env` file:
   ```
   OLLAMA_BASE_URL=http://host.docker.internal:11434
   ```
2. Start services without Ollama:
   ```bash
   docker-compose up -d
   ```
   The Ollama service won't start (it's in a profile), and the backend will use your host's Ollama.

**Option 2: Stop Host's Ollama**

1. Stop the Ollama service on your host
2. Start Docker Ollama:
   ```bash
   docker-compose --profile ollama-docker up -d
   ```

### Ollama connection issues

1. Verify Ollama is running:

   ```bash
   docker-compose ps ollama
   curl http://localhost:11434/api/tags
   ```

2. Check if model is available:

   ```bash
   docker-compose exec ollama ollama list
   ```

3. Update `.env` if Ollama is on different host:
   ```
   OLLAMA_BASE_URL=http://your-ollama-host:11434
   ```

### Port conflicts

If ports are already in use, modify `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "8001:3333" # Change 3333 to 8001
  frontend:
    ports:
      - "8080:80" # Change 80 to 8080
```

## Production Deployment

For production deployment:

1. **Change SECRET_KEY** in `.env`:

   ```bash
   # Generate a secure key
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set DEBUG=false** in `.env`:

   ```
   DEBUG=false
   ```

3. **Use PostgreSQL** instead of SQLite for better performance

4. **Configure proper CORS origins**:

   ```
   CORS_ORIGINS=https://yourdomain.com
   ```

5. **Use reverse proxy** (Nginx/Traefik) in front of Docker services

6. **Enable HTTPS** using Let's Encrypt or similar

7. **Set resource limits** in `docker-compose.yml`:

   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: "2"
             memory: 2G
   ```

8. **Regular backups** of volumes and database

## Updating the Application

1. **Pull latest code**:

   ```bash
   git pull
   ```

2. **Rebuild images**:

   ```bash
   docker-compose build
   ```

3. **Restart services**:
   ```bash
   docker-compose up -d
   ```

## Health Checks

All services include health checks. Check status:

```bash
docker-compose ps
```

Services should show `healthy` status when ready.

### Chrome Extension Access from Different Machine

If you get `404 "Conversation not found or access denied"` when using the Chrome extension from a different machine:

1. **Update CORS settings** in `.env`:

   ```
   CORS_ORIGINS=*
   ```

   This allows Chrome extension origins (`chrome-extension://`) and cross-machine access.

2. **Ensure backend is accessible** from the different machine:

   - Check firewall settings
   - Verify the backend URL in extension settings uses the correct IP/domain
   - Test connectivity: `curl http://YOUR_SERVER_IP:3333/health`

3. **Clear extension storage** and re-authenticate:

   - The conversation ID stored in the extension might be invalid
   - Go to extension options → Clear storage → Login again

4. **Verify backend URL in extension**:

   - Should be: `http://YOUR_SERVER_IP:3333` (not localhost)
   - Or if using domain: `http://yourdomain.com:3333`

5. **Check authentication token**:

   - The token might have expired
   - Re-login in the extension options page

6. **Network access**:
   - Ensure Docker port 3333 is exposed and accessible
   - Check if the backend container is bound to `0.0.0.0` (it should be by default)

## Support

For issues and questions:

- Check logs: `docker-compose logs -f`
- Review configuration in `.env`
- Verify all prerequisites are met
- Check service health: `docker-compose ps`
