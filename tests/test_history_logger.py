"""
Tests for app.services.history_logger (database-backed).

Uses the db_session fixture from conftest.py, which provides a fresh
in-memory SQLite session per test. A user row is created first since
history entries have a required foreign key to users.id.
"""

from app.db_models import User
from app.services.history_logger import load_history, log_conversation


def _create_test_user(db_session) -> User:
    user = User(username="testuser", hashed_password="not-a-real-hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_load_history_returns_empty_list_for_new_user(db_session):
    user = _create_test_user(db_session)
    assert load_history(db_session, user_id=user.id) == []


def test_log_conversation_persists_entry(db_session):
    user = _create_test_user(db_session)

    log_conversation(
        db_session,
        user_id=user.id,
        description="AI conference",
        interests=["AI", "machine learning"],
        themes=["artificial intelligence"],
        suggestions=["What got you into AI?"],
    )

    history = load_history(db_session, user_id=user.id)
    assert len(history) == 1
    assert history[0].description == "AI conference"
    assert history[0].interests == "AI, machine learning"
    assert history[0].created_at is not None


def test_load_history_returns_most_recent_first(db_session):
    user = _create_test_user(db_session)

    log_conversation(db_session, user_id=user.id, description="Event 1", interests=[], themes=[], suggestions=[])
    log_conversation(db_session, user_id=user.id, description="Event 2", interests=[], themes=[], suggestions=[])

    history = load_history(db_session, user_id=user.id)
    assert history[0].description == "Event 2"
    assert history[1].description == "Event 1"


def test_load_history_respects_limit(db_session):
    user = _create_test_user(db_session)

    for i in range(7):
        log_conversation(
            db_session, user_id=user.id, description=f"Event {i}", interests=[], themes=[], suggestions=[]
        )

    history = load_history(db_session, user_id=user.id, limit=5)
    assert len(history) == 5
