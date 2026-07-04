"""
Profile Service
-----------------
Reads and updates the personalization fields on the User row (role,
industry, networking_goal -- see app/db_models.py). Kept as its own
service module rather than inlined into the auth or conversation routers,
following the same single-responsibility convention as the other services:
if profile storage ever moves to its own table, only this file changes.

Unlike history_logger and feedback_logger, this service updates an
existing row rather than appending new ones, so there's no "load most
recent N" query here -- a user has exactly one profile, which is just the
three columns on their own User row.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.db_models import User


def update_profile(
    db: Session,
    user: User,
    role: Optional[str] = None,
    industry: Optional[str] = None,
    networking_goal: Optional[str] = None,
) -> User:
    """
    Update the given user's profile fields in place.

    Only fields explicitly passed as non-None are changed -- this lets a
    user update just one field (e.g. only their networking goal) without
    needing to resend the others, matching how the PUT /profile endpoint
    is called from the frontend's profile form.

    Args:
        db: Active database session.
        user: The User row to update (already loaded, e.g. via get_current_user).
        role: New role value, or None to leave unchanged.
        industry: New industry value, or None to leave unchanged.
        networking_goal: New networking goal value, or None to leave unchanged.

    Returns:
        The updated User row.
    """
    if role is not None:
        user.role = role
    if industry is not None:
        user.industry = industry
    if networking_goal is not None:
        user.networking_goal = networking_goal

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
