"""
Rate Limiter Configuration
------------------------------
Uses slowapi (a FastAPI-friendly wrapper around limits) to throttle the
most expensive/abusable endpoints: /generate-conversation (runs two
transformer models) and /fact-check (makes an outbound network call to
Wikipedia). Rate limiting is keyed by client IP address.

Limits are intentionally generous for local development/grading use --
the goal is to demonstrate the pattern and prevent runaway abuse, not to
heavily restrict normal use.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
