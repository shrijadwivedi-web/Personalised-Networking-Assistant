"""
Tests for app.services.feedback_logger (database-backed).
"""

import pytest

from app.db_models import User
from app.services.feedback_logger import load_feedback, log_feedback


def _create_test_user(db_session) -> User:
    user = User(username="testuser", hashed_password="not-a-real-hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_load_feedback_returns_empty_list_for_new_user(db_session):
    user = _create_test_user(db_session)
    assert load_feedback(db_session, user_id=user.id) == []


def test_log_feedback_persists_entry(db_session):
    user = _create_test_user(db_session)

    log_feedback(db_session, user_id=user.id, suggestion="Ask about their AI work", action="like")

    feedback = load_feedback(db_session, user_id=user.id)
    assert len(feedback) == 1
    assert feedback[0].suggestion == "Ask about their AI work"
    assert feedback[0].action == "like"
    assert feedback[0].created_at is not None


def test_log_feedback_rejects_invalid_action(db_session):
    user = _create_test_user(db_session)

    with pytest.raises(ValueError):
        log_feedback(db_session, user_id=user.id, suggestion="Some suggestion", action="maybe")


def test_load_feedback_respects_limit(db_session):
    user = _create_test_user(db_session)

    for i in range(15):
        log_feedback(db_session, user_id=user.id, suggestion=f"Suggestion {i}", action="like")

    feedback = load_feedback(db_session, user_id=user.id, limit=10)
    assert len(feedback) == 10
