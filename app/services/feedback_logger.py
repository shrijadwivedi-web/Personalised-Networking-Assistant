"""
Feedback Logger Service (Database-backed)
---------------------------------------------
Same rationale as history_logger.py: persists like/dislike feedback to the
`feedback` table, scoped to the authenticated user via user_id, instead of
a shared flat JSON file.
"""

from typing import List

from sqlalchemy.orm import Session

from app.db_models import Feedback

VALID_ACTIONS = {"like", "dislike"}


def log_feedback(db: Session, user_id: int, suggestion: str, action: str) -> Feedback:
    """
    Save a feedback entry for the given user.

    Args:
        db: Active database session.
        user_id: ID of the user submitting feedback.
        suggestion: The exact suggestion text being rated.
        action: Either 'like' or 'dislike'.

    Returns:
        The newly created Feedback row.

    Raises:
        ValueError: If action is not 'like' or 'dislike'.
    """
    if action not in VALID_ACTIONS:
        raise ValueError(f"action must be one of {VALID_ACTIONS}, got '{action}'")

    entry = Feedback(user_id=user_id, suggestion=suggestion, action=action)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def load_feedback(db: Session, user_id: int, limit: int = 10) -> List[Feedback]:
    """
    Load the most recent feedback entries for a user.

    Args:
        db: Active database session.
        user_id: ID of the user whose feedback to load.
        limit: Maximum number of entries to return, most recent first.

    Returns:
        A list of Feedback rows, newest first. Empty list if the user has
        submitted no feedback yet.
    """
    return (
        db.query(Feedback)
        .filter(Feedback.user_id == user_id)
        .order_by(Feedback.created_at.desc())
        .limit(limit)
        .all()
    )
