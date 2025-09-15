"""Initialize the database with tables and default data."""

from sqlalchemy import create_engine
from backend.models import Base, User
from backend.config import settings
from backend.auth import get_password_hash
from sqlalchemy.orm import sessionmaker
import sys


def init_database():
    """Initialize database with tables and default admin user."""
    
    print(f"Initializing database: {settings.DATABASE_URL}")
    
    # Create engine
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if admin user exists
        admin = db.query(User).filter(User.username == "admin").first()
        
        if not admin:
            # Create default admin user
            admin = User(
                username="admin",
                email="admin@localhost",
                hashed_password=get_password_hash("admin123"),
                full_name="Administrator",
                is_superuser=True,
                is_active=True,
                preferences={
                    "theme": "dark",
                    "model": "qwen2.5:3b",
                    "temperature": 0.7,
                    "max_steps": 10,
                    "max_tokens": 2000,
                    "require_confirmation": True
                },
                allowed_tools=[
                    "calculator",
                    "search_local_files",
                    "read_file",
                    "parse_document",
                    "web_search",
                    "query_database"
                ]
            )
            
            db.add(admin)
            db.commit()
            print("✓ Default admin user created (username: admin, password: admin123)")
            print("  ⚠️  Please change the admin password after first login!")
        else:
            print("✓ Admin user already exists")
        
        # Create demo user
        demo = db.query(User).filter(User.username == "demo").first()
        
        if not demo:
            demo = User(
                username="demo",
                email="demo@localhost",
                hashed_password=get_password_hash("demo123"),
                full_name="Demo User",
                is_superuser=False,
                is_active=True,
                preferences={
                    "theme": "light",
                    "model": "qwen2.5:3b",
                    "temperature": 0.7,
                    "max_steps": 5,
                    "max_tokens": 1000,
                    "require_confirmation": True
                },
                allowed_tools=[
                    "calculator",
                    "search_local_files",
                    "read_file"
                ]
            )
            
            db.add(demo)
            db.commit()
            print("✓ Demo user created (username: demo, password: demo123)")
        else:
            print("✓ Demo user already exists")
        
        print("\n✅ Database initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        db.rollback()
        sys.exit(1)
    
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
