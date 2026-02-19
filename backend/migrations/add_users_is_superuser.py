"""Migration: add is_superuser column to users table if missing."""

import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

from sqlalchemy import text, inspect
from backend.models.database import engine, SessionLocal


def migrate():
    """Add is_superuser to users if it doesn't exist; promote first user to admin if none."""
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return
    columns = [c["name"] for c in inspector.get_columns("users")]
    db = SessionLocal()
    try:
        if "is_superuser" not in columns:
            db.execute(text("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT 0"))
            db.commit()
        # If no admin exists, make the first user (by id) an admin
        r = db.execute(
            text("SELECT COUNT(*) as n FROM users WHERE is_superuser = 1")
        ).fetchone()
        if r and r.n == 0:
            db.execute(text("UPDATE users SET is_superuser = 1 WHERE id = (SELECT MIN(id) FROM users)"))
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
