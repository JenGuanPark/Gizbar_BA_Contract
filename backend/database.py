import os
from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

# Check for DATABASE_URL env var (provided by Render/Neon/Supabase)
# Fallback to SQLite for local development
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    # Fix for SQLAlchemy requiring 'postgresql://' instead of 'postgres://'
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # PostgreSQL connection
    engine = create_engine(DATABASE_URL, echo=True)
else:
    # SQLite fallback
    sqlite_file_name = "database.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    # check_same_thread=False is needed for SQLite with FastAPI
    connect_args = {"check_same_thread": False}
    engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    
    # Simple migration: Try adding 'reason' column if it doesn't exist
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE signal ADD COLUMN reason VARCHAR"))
            conn.commit()
            print("Added reason column")
        except Exception:
            # Ignore if column exists
            pass

def get_session():
    with Session(engine) as session:
        yield session
