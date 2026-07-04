"""
Tests for the global exception handlers registered in app/main.py.

DistilBERT load failures are hard to trigger deterministically in a test
(they'd require actually breaking network access), so that case is
covered by monkeypatching the module-level classifier to None -- the same
state app/services/event_analyzer.py is left in if model loading
genuinely fails at startup.

The conversation-generation failure case is different: that service calls
the Gemini API (see app/services/topic_generator.py and the
mock_gemini_conversation_generation fixture in tests/conftest.py, which is
applied to every test automatically -- including setting a dummy
GEMINI_API_KEY so the "no key configured" check doesn't short-circuit
before reaching the mocked call), so simulating an API failure means
overriding that fixture's mock to raise instead of return a fake
response.

Both cases verify the route returns a clean 503 rather than an unhandled
500/stack trace.
"""

from google.genai.errors import APIError

import app.services.event_analyzer as event_analyzer_module
import app.services.topic_generator as topic_generator_module


def test_analyze_event_returns_503_when_model_unavailable(client, auth_headers, monkeypatch):
    monkeypatch.setattr(event_analyzer_module, "_classifier", None)
    monkeypatch.setattr(event_analyzer_module, "_load_error", "simulated model load failure")

    response = client.post(
        "/analyze-event",
        json={"description": "AI conference"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_generate_conversation_returns_503_when_gemini_api_fails(
    client, auth_headers, mock_gemini_conversation_generation
):
    # Simulates the Gemini API rejecting the request (e.g. an invalid key).
    mock_gemini_conversation_generation.side_effect = APIError(
        code=401, response_json={"message": "Unauthorized"}
    )

    response = client.post(
        "/generate-conversation",
        json={"description": "AI conference", "interests": ["AI"]},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_generate_conversation_returns_503_when_no_gemini_key_configured(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(topic_generator_module, "GEMINI_API_KEY", None)

    response = client.post(
        "/generate-conversation",
        json={"description": "AI conference", "interests": ["AI"]},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


def test_503_response_does_not_leak_internal_error_details(client, auth_headers, monkeypatch):
    # The underlying _load_error message (which could contain internal
    # paths, URLs, or library details) must never appear in the HTTP
    # response body -- only in server-side logs.
    monkeypatch.setattr(event_analyzer_module, "_classifier", None)
    monkeypatch.setattr(
        event_analyzer_module, "_load_error", "/some/internal/path OSError: disk full"
    )

    response = client.post(
        "/analyze-event",
        json={"description": "AI conference"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "/some/internal/path" not in response.text
    assert "OSError" not in response.text
