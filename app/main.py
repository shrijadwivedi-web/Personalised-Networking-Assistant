"""
Application Entry Point
-------------------------
Creates the FastAPI app, initializes the database (creating tables on
startup if they don't exist), registers the auth and conversation routers,
wires up the slowapi rate limiter (using its standard exception handler),
and exposes a health-check endpoint.

New feature areas can be added as separate router files and included here
without touching existing code -- a hub-and-spoke routing architecture.
"""

import logging

from dotenv import load_dotenv

# Must run before importing anything that reads environment variables at
# module level (app.auth reads SECRET_KEY, app.database reads DATABASE_URL,
# and app.services.topic_generator reads GEMINI_API_KEY).
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.database import init_db
from app.rate_limit import limiter
from app.routes.auth import router as auth_router
from app.routes.conversation import router as conversation_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("networking_assistant")

app = FastAPI(
    title="Personalized Networking Assistant API",
    description=(
        "AI-powered backend that extracts themes from event descriptions, "
        "generates conversation starters, fact-checks topics via Wikipedia, "
        "and logs per-user conversation history and feedback."
    ),
    version="2.0.0",
)

# Required for the @limiter.limit(...) decorators in app/routes/conversation.py
# to function: slowapi looks up the limiter via request.app.state.limiter.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Global exception handlers
# ---------------------------------------------------------------------------
# Registering these here (rather than wrapping every route body in its own
# try/except) keeps error handling in one place instead of duplicated
# across app/routes/conversation.py. FastAPI/Starlette dispatch to the
# handler matching the exception's exact type -- HTTPException (used for
# the 401s/404s/409s raised elsewhere in this app) already has its own
# built-in handler and is unaffected by the handlers below.
#
# None of these expose a raw stack trace to the client: every response
# body is a short, fixed, human-readable message. The real exception is
# always logged server-side via logger.error/exception for debugging.

@app.exception_handler(RuntimeError)
async def model_unavailable_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """
    Raised by app/services/event_analyzer.py and app/services/
    topic_generator.py when their underlying Hugging Face model failed to
    download/load at startup (no network, Hugging Face Hub unreachable,
    corrupted cache, etc). Translated into a 503 -- the request was
    otherwise valid, the *service* is what's temporarily unavailable.
    """
    logger.error("Model unavailable while handling %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={
            "detail": "This feature is temporarily unavailable because an AI "
                      "model failed to load. Please try again shortly, or "
                      "check the server logs if this persists."
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Covers connection issues, integrity errors not already caught by a
    route, locked-database errors, etc. The specific SQLAlchemy exception
    is logged in full server-side; the client only ever sees a generic,
    safe message."""
    logger.exception("Database error while handling %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last-resort catch-all for anything not covered by a more specific
    handler above (or by FastAPI's built-in HTTPException/validation
    handling). Ensures no unexpected error can ever reach the client as a
    raw traceback -- logger.exception captures the full trace for
    debugging, but the HTTP response stays generic."""
    logger.exception("Unhandled exception while handling %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("Database initialized and application startup complete.")


app.include_router(auth_router)
app.include_router(conversation_router)


@app.get("/")
def health_check() -> dict:
    """Simple health-check endpoint used to verify the API is up and reachable."""
    return {"status": "ok", "service": "Personalized Networking Assistant API"}
