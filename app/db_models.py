"""
SQLAlchemy ORM Models
-----------------------
Three tables:
  - users: registered accounts (hashed passwords only, never plaintext)
  - conversation_history: one row per generated conversation, scoped to a user
  - feedback: one row per like/dislike on a suggestion, scoped to a user

Both conversation_history and feedback have a foreign key to users.id, so
each user only ever sees their own history/feedback -- this is the data
isolation that replaces the old single shared JSON files.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Profile fields used to personalize generated conversation starters.
    # All nullable: a brand-new user has no profile yet, and generation
    # must still work (falling back to generic phrasing) before they fill
    # this in. See app/services/topic_generator.py for how these are used.
    role = Column(String(120), nullable=True)
    industry = Column(String(120), nullable=True)
    networking_goal = Column(Text, nullable=True)

    history_entries = relationship(
        "ConversationHistory", back_populates="user", cascade="all, delete-orphan"
    )
    feedback_entries = relationship(
        "Feedback", back_populates="user", cascade="all, delete-orphan"
    )


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    interests = Column(Text, nullable=False)  # stored as a comma-joined string
    themes = Column(Text, nullable=False)  # stored as a comma-joined string
    suggestions = Column(Text, nullable=False)  # stored as a newline-joined string
    tone = Column(String(32), nullable=True)  # 'formal' / 'casual' / 'witty', None for legacy rows
    confidence_scores = Column(Text, nullable=True)  # comma-joined ints, parallel to suggestions
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="history_entries")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    suggestion = Column(Text, nullable=False)
    action = Column(String(16), nullable=False)  # 'like' or 'dislike'
    created_at = Column(DateTime, default=_utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="feedback_entries")
