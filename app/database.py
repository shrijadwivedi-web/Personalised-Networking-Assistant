"""
Database Engine & Session Setup
----------------------------------
Uses SQLite via SQLAlchemy. SQLite is chosen deliberately for this project:
zero external setup (no separate DB server to install/configure), a single
portable file, and more than sufficient for a small, locally-run/grading-
scale application. DATABASE_URL is read from the environment so it can be
swapped for Postgres/MySQL in a real deployment without code changes.
"""

import os
import re
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "data" / "app.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

IS_SQLITE = DATABASE_URL.startswith("sqlite")

# check_same_thread=False is required for SQLite when accessed from multiple
# threads (FastAPI's default worker model). This is safe here because each
# request gets its own session via get_db().
connect_args = {"check_same_thread": False} if IS_SQLITE else {}


def _ensure_sqlite_parent_dir_exists(database_url: str) -> None:
    """
    Ensure the parent directory of a SQLite file-based DATABASE_URL exists,
    creating it if necessary. Without this, create_engine() succeeds (it
    doesn't touch the filesystem yet) but the first actual query fails with
    'unable to open database file', since SQLite won't create missing
    parent directories on its own.

    Handles both 3-slash (relative path, e.g. sqlite:///data/app.db) and
    4-slash (absolute path, e.g. sqlite:////app/data/app.db) forms. The
    special in-memory URL (sqlite:///:memory:) is left alone.
    """
    if ":memory:" in database_url:
        return

    match = re.match(r"^sqlite:///(.*)$", database_url)
    if not match:
        return

    db_path = Path(match.group(1))
    db_path.parent.mkdir(parents=True, exist_ok=True)


if IS_SQLITE:
    _ensure_sqlite_parent_dir_exists(DATABASE_URL)

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session and ensures it's
    closed after the request completes, even if an exception occurs."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op if tables exist)."""
    # Importing models here (rather than at module level) avoids circular
    # imports, since db_models.py imports Base from this module.
    from app import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
