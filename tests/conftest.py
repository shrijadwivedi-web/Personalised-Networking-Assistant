"""
Shared pytest fixtures.

- Ensures the project root is on sys.path so `import app.xxx` works
  regardless of which directory pytest is invoked from.
- Provides a `db_session` fixture backed by a fresh in-memory SQLite
  database per test, so tests never touch the real data/app.db file and
  don't leak state between tests.
- Provides a `client` fixture: a FastAPI TestClient with the app's
  get_db dependency overridden to use the in-memory test database.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def mock_gemini_conversation_generation(monkeypatch):
    """
    Applied automatically to every test in the suite. Conversation
    generation (app/services/topic_generator.py) now calls the Gemini API
    over the network -- a real, paid, external service that integration
    tests should never depend on (it would make the suite flaky, slow,
    and unrunnable without a valid GEMINI_API_KEY and internet access).
    This replaces that network call with a fixed, realistic 3-line
    response for the duration of every test.

    Also monkeypatches GEMINI_API_KEY to a dummy truthy value: without
    this, generate_topics()'s own "no key configured" check would raise
    RuntimeError before ever reaching the mocked call below, and every
    integration test that hits /generate-conversation (in
    tests/test_routes.py) would get a 503 instead of the 200 it expects.
    Tests that specifically want to exercise the "no key configured" path
    (see tests/test_error_handling.py and tests/test_topic_generator.py)
    override this back to None for just that test.

    Yields the mock itself so individual tests can override its behavior
    (e.g. tests/test_error_handling.py sets .side_effect to simulate an
    API failure) or more specific @patch decorators in
    tests/test_topic_generator.py can layer their own return values on
    top for the duration of just that test.

    DistilBERT theme extraction (app/services/event_analyzer.py) is
    intentionally NOT mocked here -- it runs locally with no network
    dependency once its model weights are cached, so there's no reason to
    fake it out the same way.
    """
    monkeypatch.setattr("app.services.topic_generator.GEMINI_API_KEY", "dummy-test-key")

    fake_response = SimpleNamespace(
        text=(
            "1. What drew you to this event?\n"
            "2. What's your background in this space?\n"
            "3. What are you hoping to get out of today?"
        )
    )

    with patch(
        "app.services.topic_generator._client.models.generate_content",
        return_value=fake_response,
    ) as mock_generate_content:
        yield mock_generate_content


@pytest.fixture()
def test_engine():
    """A fresh in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keeps the same in-memory DB alive across connections
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(test_engine):
    """A SQLAlchemy session bound to the per-test in-memory engine."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(test_engine):
    """
    A FastAPI TestClient with get_db overridden to use the per-test
    in-memory database, instead of the real SQLite file on disk.
    """
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """
    Registers a fresh test user, logs in, and returns Authorization
    headers carrying a valid bearer token for that user.
    """
    client.post("/auth/register", json={"username": "testuser", "password": "testpassword123"})
    response = client.post(
        "/auth/login", json={"username": "testuser", "password": "testpassword123"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
