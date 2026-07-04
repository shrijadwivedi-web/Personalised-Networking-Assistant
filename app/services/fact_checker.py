"""
Fact Checker Service
---------------------
Provides quick topic verification by querying Wikipedia's REST summary API.

Design philosophy: keep this simple and dependency-free. Wikipedia's public
REST API requires no API key, returns clean structured JSON, and is reliable
enough for the "quick fact check before a conversation" use case this app
targets. We deliberately don't try to do anything fancier (full-text search,
disambiguation handling) -- if the page isn't found or the network call
fails, we fall back to a friendly message instead of crashing the request.
"""

import requests

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
REQUEST_TIMEOUT_SECONDS = 5
FALLBACK_MESSAGE = "Sorry, we couldn't find reliable information on that topic right now."


def fact_check(query: str) -> str:
    """
    Look up a short summary for `query` via the Wikipedia REST API.

    Args:
        query: The topic or phrase to look up.

    Returns:
        A short text extract describing the topic, or a fallback message
        if the lookup fails for any reason (network error, timeout,
        page not found, unexpected response shape).
    """
    if not query or not query.strip():
        return FALLBACK_MESSAGE

    url = WIKIPEDIA_SUMMARY_URL.format(query.strip().replace(" ", "_"))

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        extract = data.get("extract")
        if not extract:
            return FALLBACK_MESSAGE
        return extract
    except (requests.RequestException, ValueError):
        # ValueError covers JSON decoding failures; RequestException covers
        # connection errors, timeouts, and non-2xx HTTP status codes.
        return FALLBACK_MESSAGE
