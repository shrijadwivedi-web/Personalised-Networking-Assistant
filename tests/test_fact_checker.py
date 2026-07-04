"""
Tests for app.services.fact_checker.

Fact checker tests mock the network call (requests.get) rather than hitting
the real Wikipedia API. This keeps tests fast, deterministic, and runnable
without internet access (important for CI/CD pipelines). We cover three
paths: the happy path (valid extract returned), the missing-data path (200
response but no 'extract' field), and the error path (network failure).
"""

from unittest.mock import MagicMock, patch

import requests

from app.services.fact_checker import FALLBACK_MESSAGE, fact_check


@patch("app.services.fact_checker.requests.get")
def test_fact_check_happy_path(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"extract": "Blockchain is a distributed ledger technology."}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = fact_check("blockchain")

    assert result == "Blockchain is a distributed ledger technology."


@patch("app.services.fact_checker.requests.get")
def test_fact_check_missing_extract_returns_fallback(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # no "extract" key
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = fact_check("an obscure made-up topic")

    assert result == FALLBACK_MESSAGE


@patch("app.services.fact_checker.requests.get")
def test_fact_check_network_error_returns_fallback(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("network down")

    result = fact_check("blockchain")

    assert result == FALLBACK_MESSAGE


def test_fact_check_empty_query_returns_fallback():
    assert fact_check("") == FALLBACK_MESSAGE
    assert fact_check("   ") == FALLBACK_MESSAGE
