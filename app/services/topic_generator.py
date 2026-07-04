"""
Topic Generator Service
------------------------
Generates natural-sounding conversation starters using Google's Gemini
API. This intentionally replaces an earlier local GPT-2 implementation
(and, briefly, a Hugging Face Inference Providers-based version): GPT-2
Small is not instruction-tuned, so getting it to reliably produce a
clean, on-topic list of starters required fragile prompt engineering and
post-hoc output cleaning. An instruction-tuned model can simply be told
"return exactly 3 conversation starters, nothing else" and follow that
directly.

This is a deliberate architectural split from app/services/
event_analyzer.py, which still runs DistilBERT locally via
transformers.pipeline(). That's intentional, not an oversight:
zero-shot classification with a small model like DistilBERT is fast and
accurate enough to run on CPU with no noticeable latency, so there's no
reason to add a network dependency for it. Conversation generation is a
different story -- a small local generative model produces noticeably
worse text than a modern hosted model, and running a model that size
locally on CPU would be far too slow for an interactive request. Calling
a hosted API is the practical tradeoff: much better output, in exchange
for a network dependency and per-request latency that a locally-loaded
model wouldn't have.

Authentication: GEMINI_API_KEY is read from the environment (populated
from .env via python-dotenv, loaded in app/main.py before this module is
imported). It is never hardcoded and never logged. Client construction
(genai.Client(...)) is instant and does not itself validate the key or
reach the network -- failures instead happen per-request (missing/invalid
key, the Gemini API being unreachable, the model being temporarily
overloaded, etc). Those are caught in generate_topics() below and
re-raised as RuntimeError, which app/main.py's global exception handler
already converts into a clean 503 -- the same mechanism used for the
DistilBERT load-failure case, reused here rather than duplicated.
"""

import logging
import os
from typing import List, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger("networking_assistant")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or None

# Overridable via env var so a different Gemini model can be swapped in
# without a code change -- e.g. a faster or higher-quality alternative as
# new versions become available. gemini-2.5-flash is Google's fast,
# cost-effective, generally-available (non-preview) model, which made it
# the more practical default for a project meant to run out of the box
# without needing to track preview-model churn.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

MAX_OUTPUT_TOKENS = 250
GENERATION_TEMPERATURE = 0.8

VALID_TONES = ("formal", "casual", "witty")

_TONE_DESCRIPTIONS = {
    "formal": "a polished, professional tone",
    "casual": "a relaxed, conversational tone",
    "witty": "a playful, witty tone",
}

SYSTEM_INSTRUCTION = (
    "You write short, natural-sounding conversation starters for "
    "networking events. Respond with exactly 3 conversation starters "
    "as a numbered list (1. 2. 3.) and nothing else -- no introduction, "
    "no explanation, no closing remarks. Each starter should be one "
    "sentence, sound natural to say out loud, and ideally end in a "
    "question so the other person has something easy to respond to."
)

# Built once at import time -- cheap, since it does not itself make a
# network call. Always constructed, even with no real key configured
# (falling back to a placeholder string rather than passing None) so
# there is always a real client object to call -- generate_topics() below
# explicitly checks GEMINI_API_KEY before ever using it, so the
# placeholder value itself is never actually sent in a request.
_client: genai.Client = genai.Client(api_key=GEMINI_API_KEY or "unconfigured")

if not GEMINI_API_KEY:
    logger.warning(
        "GEMINI_API_KEY is not set. Conversation generation will fail at "
        "request time until a valid key is added to .env -- see "
        ".env.example. Theme extraction (DistilBERT, run locally) is "
        "unaffected."
    )


def _build_user_message(
    themes: List[str],
    interests: List[str],
    tone: str,
    role: Optional[str] = None,
    industry: Optional[str] = None,
    networking_goal: Optional[str] = None,
) -> str:
    """
    Build the user-facing prompt text sent to Gemini alongside
    SYSTEM_INSTRUCTION. Using an explicit system instruction (rather than
    trying to coax a format out of a raw text continuation, as the old
    GPT-2 prompt had to) is the main advantage of moving to an
    instruction-tuned model: the output-format contract is stated
    directly instead of implied.
    """
    theme_text = ", ".join(themes) if themes else "general topics"
    interest_text = ", ".join(interests) if interests else "meeting new people"
    tone_description = _TONE_DESCRIPTIONS.get(tone, _TONE_DESCRIPTIONS["casual"])

    message = (
        f"I'm attending an event focused on {theme_text}. "
        f"I'm personally interested in {interest_text}."
    )
    if role:
        message += f" I work as a {role}."
    if industry:
        message += f" I'm in the {industry} industry."
    if networking_goal:
        message += f" My goal for networking right now is: {networking_goal}."
    message += f" Write the 3 starters in {tone_description}."

    return message


def _clean_line(line: str) -> str:
    """Strip leading numbering/bullets and surrounding whitespace from a line."""
    cleaned = line.strip()
    for prefix in ("1.", "2.", "3.", "-", "*", "•"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _looks_like_list_item(line: str) -> bool:
    """True if a raw (uncleaned) line looks like a numbered/bulleted list
    entry, as opposed to a preface or closing sentence a model might add
    despite being asked not to (e.g. 'Sure! Here are 3 starters:')."""
    stripped = line.strip()
    if not stripped:
        return False
    return stripped[0].isdigit() or stripped[0] in ("-", "*", "•")


def _parse_suggestions(generated_text: str) -> List[str]:
    """
    Turn the model's raw response text into a clean list of up to 3
    suggestions. Prefers lines that look like list items (see
    _looks_like_list_item); if none are found -- e.g. the model responded
    in plain prose despite the system instruction -- falls back to
    treating every non-empty line as a suggestion, so a differently
    formatted but otherwise valid response still surfaces something
    instead of an empty result.
    """
    lines = [line for line in generated_text.split("\n") if line.strip()]

    list_item_lines = [line for line in lines if _looks_like_list_item(line)]
    lines_to_use = list_item_lines if list_item_lines else lines

    suggestions = [_clean_line(line) for line in lines_to_use]
    suggestions = [s for s in suggestions if s]
    return suggestions[:3]


def generate_topics(
    themes: List[str],
    interests: List[str],
    tone: str = "casual",
    role: Optional[str] = None,
    industry: Optional[str] = None,
    networking_goal: Optional[str] = None,
) -> List[str]:
    """
    Generate up to 3 conversation starter suggestions via the Gemini API
    (see GEMINI_MODEL).

    Args:
        themes: Themes extracted from the event description (see
            app/services/event_analyzer.py -- still DistilBERT, run locally).
        interests: The user's stated interests.
        tone: Desired tone -- one of 'formal', 'casual', 'witty'. Falls
            back to 'casual' for any unrecognized value.
        role: Optional profile field (e.g. "backend developer").
        industry: Optional profile field (e.g. "fintech").
        networking_goal: Optional profile field, free text.

    Returns:
        A list of up to 3 non-empty conversation starter strings.

    Raises:
        RuntimeError: if the request to the Gemini API fails for any
            reason (missing/invalid GEMINI_API_KEY, network error, the
            model being temporarily overloaded, etc). Routes calling this
            should let RuntimeError propagate -- app/main.py's global
            exception handler converts it into a 503 automatically.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "Conversation generation model is unavailable: GEMINI_API_KEY is not set."
        )

    if tone not in VALID_TONES:
        tone = "casual"

    user_message = _build_user_message(
        themes, interests, tone=tone, role=role, industry=industry,
        networking_goal=networking_goal,
    )

    try:
        response = _client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=GENERATION_TEMPERATURE,
            ),
        )
    except APIError as exc:
        # Covers invalid/missing key (401/403), rate limiting (429), and
        # the model being temporarily unavailable (503) -- all surfaced
        # with the same friendly 503 by app/main.py, since from the
        # user's point of view this feature is just "not available right
        # now" regardless of which of these caused it.
        raise RuntimeError(
            f"Conversation generation request to Gemini failed: {exc}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - network/timeout/anything else
        raise RuntimeError(
            f"Conversation generation request failed unexpectedly: {exc}"
        ) from exc

    generated_text = response.text or ""
    return _parse_suggestions(generated_text)
