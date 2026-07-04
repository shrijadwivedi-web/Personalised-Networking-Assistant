"""
Tests for app.services.event_analyzer.

These tests validate structural properties of the output rather than
asserting specific themes, since the exact themes returned depend on the
DistilBERT model's learned weights and could shift slightly with model
updates. What should NOT change is the contract: a list of at most 3
strings, drawn from the candidate labels, with at least one result for
non-empty input.
"""

from app.services.event_analyzer import DEFAULT_THEMES, extract_event_themes


def test_returns_a_list():
    result = extract_event_themes("A conference about renewable energy")
    assert isinstance(result, list)


def test_returns_at_most_three_themes():
    result = extract_event_themes("A conference about renewable energy")
    assert len(result) <= 3


def test_returns_at_least_one_theme_for_valid_input():
    result = extract_event_themes("A conference about renewable energy")
    assert len(result) >= 1


def test_themes_are_drawn_from_candidate_labels():
    custom_labels = ["finance", "healthcare", "education"]
    result = extract_event_themes("A panel on hospital funding", custom_labels)
    assert all(theme in custom_labels for theme in result)


def test_default_labels_used_when_none_provided():
    result = extract_event_themes("A panel on AI ethics")
    assert all(theme in DEFAULT_THEMES for theme in result)


def test_empty_description_returns_empty_list():
    assert extract_event_themes("") == []


def test_whitespace_only_description_returns_empty_list():
    assert extract_event_themes("   ") == []
