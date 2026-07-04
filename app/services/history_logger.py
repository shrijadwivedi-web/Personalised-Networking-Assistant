"""
History Logger Service (Database-backed)
--------------------------------------------
Persists generated conversations to the conversation_history table, scoped
to the authenticated user via user_id. This replaces the original flat
JSON-file implementation: moving to SQLite gives us per-user data isolation
(required once auth was introduced), safe concurrent writes (SQLite handles
locking internally, unlike hand-rolled read-modify-write JSON), and
efficient querying (e.g. "most recent 5 for this user" via SQL rather than
loading and slicing the entire file into memory).

List fields (interests, themes, suggestions, confidence_scores) are stored
as delimited text columns rather than a separate normalized table, since
they're always read and written as a whole alongside their parent entry --
introducing extra tables here would add joins without a corresponding
benefit.
"""

from typing import List, Optional

from sqlalchemy.orm import Session

from app.db_models import ConversationHistory


def log_conversation(
    db: Session,
    user_id: int,
    description: str,
    interests: List[str],
    themes: List[str],
    suggestions: List[str],
    tone: Optional[str] = None,
    confidence_scores: Optional[List[int]] = None,
) -> ConversationHistory:
    """
    Save a conversation entry for the given user.

    Args:
        db: Active database session.
        user_id: ID of the user this conversation belongs to.
        description: The event description supplied by the user.
        interests: The user's stated interests.
        themes: Themes extracted from the description.
        suggestions: Generated conversation starter suggestions.
        tone: The tone used for generation ('formal'/'casual'/'witty'), or
            None for older calls that predate the tone feature.
        confidence_scores: Parallel list of int scores (see app/services/
            scorer.py), or None if scoring wasn't performed.

    Returns:
        The newly created ConversationHistory row.
    """
    entry = ConversationHistory(
        user_id=user_id,
        description=description,
        interests=", ".join(interests),
        themes=", ".join(themes),
        suggestions="\n".join(suggestions),
        tone=tone,
        confidence_scores=(
            ", ".join(str(s) for s in confidence_scores) if confidence_scores else None
        ),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def load_history(db: Session, user_id: int, limit: int = 5) -> List[ConversationHistory]:
    """
    Load the most recent conversation history entries for a user.

    Args:
        db: Active database session.
        user_id: ID of the user whose history to load.
        limit: Maximum number of entries to return, most recent first.

    Returns:
        A list of ConversationHistory rows, newest first. Empty list if
        the user has no history yet.
    """
    return (
        db.query(ConversationHistory)
        .filter(ConversationHistory.user_id == user_id)
        .order_by(ConversationHistory.created_at.desc())
        .limit(limit)
        .all()
    )
