import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load variables from backend/.env into the environment
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set. Make sure backend/.env exists and contains it."
    )

# The engine manages the actual connection pool to Neon
engine = create_engine(DATABASE_URL)

# Each request will get its own Session from this factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# All our SQLAlchemy models (Phase 3 onward) will inherit from this Base
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and always closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()