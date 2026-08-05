"""
Tests for app.services.topic_generator.

Conversation generation now calls Google's Gemini API over the network
(see the module docstring in app/services/topic_generator.py for why this
differs from event_analyzer.py's local DistilBERT pipeline). These tests
mock the client's generate_content call rather than hitting the real,
paid, network-dependent API -- same rationale as test_fact_checker.py's
mocking of the Wikipedia call: fast, deterministic, and runnable without
internet access or a real GEMINI_API_KEY.

All tests here rely on tests/conftest.py's autouse fixture, which already
sets GEMINI_API_KEY to a dummy truthy value and mocks the underlying
client call for the whole suite -- so generate_topics() doesn't
short-circuit on its own "no key configured" check before reaching the
mocked API call. The one test here that specifically wants to exercise
that check (test_no_api_key_configured_raises_runtime_error) overrides it
back to None for just that test.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from google.genai.errors import APIError

from app.services.topic_generator import generate_topics, _parse_suggestions


def _mock_response(text: str):
    """Build a fake object shaped like the real GenerateContentResponse
    returned by client.models.generate_content, with just enough
    structure for generate_topics() to read response.text."""
    return SimpleNamespace(text=text)


@patch("app.services.topic_generator._client.models.generate_content")
def test_returns_a_list_of_parsed_suggestions(mock_generate_content):
    mock_generate_content.return_value = _mock_response(
        "1. What drew you to this event?\n"
        "2. How are you thinking about AI in your work?\n"
        "3. What's been the highlight so far?"
    )

    result = generate_topics(["AI", "sustainability"], ["climate change"])

    assert isinstance(result, list)
    assert len(result) == 3
    assert result[0] == "What drew you to this event?"


@patch("app.services.topic_generator._client.models.generate_content")
def test_returns_at_most_three_suggestions_even_if_model_returns_more(mock_generate_content):
    mock_generate_content.return_value = _mock_response(
        "1. First starter?\n2. Second starter?\n3. Third starter?\n4. Fourth starter?"
    )

    result = generate_topics(["AI"], ["technology"])
    assert len(result) <= 3


@patch("app.services.topic_generator._client.models.generate_content")
def test_suggestions_are_non_empty_strings(mock_generate_content):
    mock_generate_content.side_effect = [
        _mock_response(
            "1. What's exciting to you about this space?\n2. Have you been before?"
        ),
        _mock_response("1. What project are you most excited about right now?"),
    ]

    result = generate_topics(["AI", "sustainability"], ["climate change"])
    for suggestion in result:
        assert isinstance(suggestion, str)
        assert suggestion.strip() != ""


@patch("app.services.topic_generator._client.models.generate_content")
def test_handles_empty_themes_and_interests_gracefully(mock_generate_content):
    mock_generate_content.return_value = _mock_response(
        "1. What brings you here today?\n"
        "2. What has been your favorite session?\n"
        "3. Who were you hoping to meet?"
    )

    result = generate_topics([], [])
    assert isinstance(result, list)


@patch("app.services.topic_generator._client.models.generate_content")
def test_invalid_tone_falls_back_to_casual_without_raising(mock_generate_content):
    mock_generate_content.return_value = _mock_response(
        "1. What brings you here today?\n"
        "2. What has caught your attention so far?\n"
        "3. What are you working on right now?"
    )

    # Should not raise even though "sarcastic" isn't a supported tone.
    result = generate_topics(["AI"], ["technology"], tone="sarcastic")
    assert isinstance(result, list)


@patch("app.services.topic_generator._client.models.generate_content")
def test_api_failure_is_translated_to_runtime_error(mock_generate_content):
    # Covers invalid/missing key, rate-limit, and model-unavailable cases
    # -- all raised by the SDK as APIError and all translated the same
    # way, since app/main.py's global handler turns any RuntimeError from
    # this module into a 503.
    mock_generate_content.side_effect = APIError(
        code=401, response_json={"message": "Unauthorized"}
    )

    with pytest.raises(RuntimeError):
        generate_topics(["AI"], ["technology"])


@patch("app.services.topic_generator._client.models.generate_content")
def test_unexpected_failure_is_also_translated_to_runtime_error(mock_generate_content):
    mock_generate_content.side_effect = TimeoutError("request timed out")

    with pytest.raises(RuntimeError):
        generate_topics(["AI"], ["technology"])


def test_no_api_key_configured_raises_runtime_error(monkeypatch):
    monkeypatch.setattr("app.services.topic_generator.GEMINI_API_KEY", None)

    with pytest.raises(RuntimeError):
        generate_topics(["AI"], ["technology"])


def test_parse_suggestions_falls_back_to_all_lines_if_no_list_items_found():
    # If the model ignores the numbered-list instruction and just writes
    # plain sentences, parsing should still surface something rather than
    # returning an empty list.
    result = _parse_suggestions("What drew you here?\nHow's the event so far?")
    assert result == ["What drew you here?", "How's the event so far?"]


def test_parse_suggestions_prefers_list_items_over_preface_text():
    # A common instruction-tuned-model quirk: adding a preface sentence
    # despite being told not to. List-item lines should be preferred.
    result = _parse_suggestions(
        "Sure! Here are 3 great conversation starters for you:\n"
        "1. What brought you to this event?\n"
        "2. What's your take on AI in this space?"
    )
    assert result == ["What brought you to this event?", "What's your take on AI in this space?"]


@patch("app.services.topic_generator._client.models.generate_content")
def test_retries_and_combines_unique_items_when_first_response_has_only_two(
    mock_generate_content,
):
    mock_generate_content.side_effect = [
        _mock_response("1. First starter?\n2. Second starter?"),
        _mock_response("1. First starter?\n2. Third starter?\n3. Fourth starter?"),
    ]

    result = generate_topics(["AI"], ["Python"])

    assert result == ["First starter?", "Second starter?", "Third starter?"]
    assert mock_generate_content.call_count == 2


@patch("app.services.topic_generator._client.models.generate_content")
def test_raises_if_two_attempts_still_cannot_produce_three_items(mock_generate_content):
    mock_generate_content.return_value = _mock_response("1. Only one starter?")

    with pytest.raises(RuntimeError, match="fewer than three"):
        generate_topics(["AI"], ["Python"])

    assert mock_generate_content.call_count == 2


@patch("app.services.topic_generator._client.models.generate_content")
def test_truncated_line_does_not_count_as_a_complete_starter(mock_generate_content):
    mock_generate_content.side_effect = [
        _mock_response(
            "1. First complete starter?\n"
            "2. Second complete starter?\n"
            "3. This sentence was cut off in the middle of"
        ),
        _mock_response("1. Third complete starter?"),
    ]

    result = generate_topics(["AI"], ["Python"])

    assert result == [
        "First complete starter?",
        "Second complete starter?",
        "Third complete starter?",
    ]
