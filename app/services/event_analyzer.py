"""
Event Analyzer Service
-----------------------
Responsible for extracting themes from a free-text event description.

We use Hugging Face's zero-shot-classification pipeline with DistilBERT.
Zero-shot classification lets us score a description against ANY list of
candidate labels without needing to train or fine-tune a model on those
specific categories first. That's important here because we can't know in
advance every possible type of networking event a user might describe.

The pipeline is instantiated once, at import time, rather than inside the
function. Loading a transformer model is relatively slow (on the order of
seconds), so doing it once at startup means every subsequent API request
is fast -- the cost is paid once when the server starts, not on every call.

Model loading is wrapped in a try/except rather than left to fail loudly
at import time. If the model can't be downloaded (no network, Hugging Face
Hub is unreachable, disk full, etc.), the whole application would
otherwise fail to start -- taking down auth, history, profile, and every
other unrelated endpoint along with it. Instead, the failure is logged
once at startup, and only requests that actually need this model receive
a clear 503 error (see extract_event_themes below) while the rest of the
app keeps working normally.
"""

import logging
from typing import List, Optional

from transformers import pipeline

logger = logging.getLogger("networking_assistant")

# No authentication token needed here: typeform/distilbert-base-uncased-mnli
# is a public model and downloads anonymously from Hugging Face. This
# service has no dependency on Hugging Face's Inference API or any API
# key -- it only downloads model weights once and then runs entirely
# locally. (Conversation generation, in app/services/topic_generator.py,
# is the one AI feature in this app that calls a hosted API and needs a
# key -- GEMINI_API_KEY -- and that's unrelated to this file.)

DEFAULT_THEMES = [
    "artificial intelligence",
    "healthcare",
    "blockchain",
    "education",
    "sustainability",
    "finance",
    "climate change",
    "urban planning",
    "entrepreneurship",
    "cybersecurity",
]

_classifier = None
_load_error: Optional[str] = None

try:
    _classifier = pipeline(
        "zero-shot-classification",
        model="typeform/distilbert-base-uncased-mnli",
    )
except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure
    # here (network, disk, corrupted cache, etc.) should degrade this one
    # feature, not crash the whole application at startup.
    _load_error = str(exc)
    logger.error(
        "Failed to load the theme-extraction model (typeform/distilbert-"
        "base-uncased-mnli). Theme extraction and conversation generation "
        "will return a 503 until this is resolved. Underlying error: %s",
        exc,
    )


def extract_event_themes(
    description: str,
    candidate_labels: Optional[List[str]] = None,
) -> List[str]:
    """
    Extract the top themes from an event description.

    Args:
        description: Free-text description of the networking event.
        candidate_labels: Optional custom list of labels to classify against.
            Defaults to DEFAULT_THEMES if not provided.

    Returns:
        A list of up to 3 theme strings, ordered from most to least relevant.

    Raises:
        RuntimeError: if the underlying model failed to load at startup.
            Routes calling this should catch RuntimeError and translate it
            into a 503 response -- see app/routes/conversation.py.
    """
    if _classifier is None:
        raise RuntimeError(
            f"Theme extraction model is unavailable: {_load_error}"
        )

    labels = candidate_labels if candidate_labels else DEFAULT_THEMES

    if not description or not description.strip():
        return []

    result = _classifier(description, candidate_labels=labels, multi_label=True)

    # result["labels"] is already sorted by descending score by the pipeline.
    top_themes = result["labels"][:3]
    return top_themes
