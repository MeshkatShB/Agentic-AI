#!/bin/bash
set -e

echo "🚀 Starting Local AI Agent Backend..."

# Wait for database to be ready (if using external database)
if [ -n "$DATABASE_URL" ] && [[ "$DATABASE_URL" == postgresql* ]]; then
    echo "⏳ Waiting for database..."
    # Try to connect using psycopg2 if available, otherwise skip
    python -c "import psycopg2" 2>/dev/null && {
        until python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; do
            echo "Database is unavailable - sleeping"
            sleep 1
        done
        echo "✅ Database is ready"
    } || echo "⚠️  psycopg2 not available, skipping database wait"
fi

# Initialize database if it doesn't exist (for SQLite)
if [[ "$DATABASE_URL" == sqlite* ]] || [ -z "$DATABASE_URL" ]; then
    # Extract database path from DATABASE_URL
    # Handle formats: sqlite:///./path, sqlite:///path, sqlite:////absolute/path
    DB_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///\./||' | sed 's|sqlite:///||' | sed 's|sqlite://||')
    
    # If path is empty or just ".", use default
    if [ -z "$DB_PATH" ] || [ "$DB_PATH" == "." ]; then
        DB_PATH="db/local_agent.db"
    fi
    
    DB_DIR=$(dirname "$DB_PATH")
    
    # Create database directory if it doesn't exist
    if [ -n "$DB_DIR" ] && [ "$DB_DIR" != "." ]; then
        echo "📁 Creating database directory: $DB_DIR"
        mkdir -p "$DB_DIR"
        chmod 755 "$DB_DIR" || true
    fi
    
    # Check if database file exists
    if [ ! -f "$DB_PATH" ]; then
        echo "🗄️ Initializing database at $DB_PATH..."
        python backend/init_db.py || echo "⚠️  Database initialization failed, continuing anyway..."
    else
        echo "✅ Database already exists at $DB_PATH"
    fi
    
    # Ensure database file and directory have write permissions
    if [ -f "$DB_PATH" ]; then
        chmod 664 "$DB_PATH" || true
    fi
    if [ -d "$DB_DIR" ]; then
        chmod 755 "$DB_DIR" || true
    fi
fi

# Run migrations (order: tables first, then columns)
echo "🔄 Running migrations..."
python -c "
import sys
MIGRATIONS = [
    ('add_file_attachments_column', 'File attachments'),
    ('create_mcp_servers_table', 'MCP servers'),
    ('add_last_tool_count_column', 'Tool count'),
    ('add_users_is_superuser', 'Users is_superuser'),
    ('create_cron_jobs_table', 'Cron jobs'),
    ('create_cron_job_runs_table', 'Cron job runs'),
    ('add_cron_job_schedule_timezone', 'Cron job timezone'),
    ('create_user_notifications_table', 'User notifications'),
    ('create_telegram_pairing_table', 'Telegram pairing'),
]
for mod_name, label in MIGRATIONS:
    try:
        mod = __import__(f'backend.migrations.{mod_name}', fromlist=['migrate'])
        mod.migrate()
        print(f'✓ {label} migration complete')
    except ImportError as e:
        print(f'Could not import {mod_name}: {e}')
    except Exception as e:
        print(f'Migration check ({mod_name}): {e}')
" || echo "⚠️  Some migrations may have failed, continuing..."

echo "✅ Backend initialization complete"
echo "🚀 Starting server..."

# Execute the main command
exec "$@"

