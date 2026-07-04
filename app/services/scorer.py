"""
Icebreaker Confidence Scorer
-------------------------------
Rates each generated conversation starter on a 1-5 scale, with a short
human-readable explanation of why it received that score.

Deliberately rule-based rather than model-based: the conversation-
generation model's own output
quality is uneven, and using a second model to grade the first model's
output would add latency and a second point of failure for very little
benefit at this scale. A small set of interpretable heuristics is also
easier to defend, debug, and unit-test than a black-box score would be --
every score this module produces can be explained in one sentence.

The heuristics look at structural properties known to correlate with a
*usable* icebreaker: is it a real question (questions invite a reply,
rather than a flat statement the other person has to do all the work to
respond to), is it a reasonable length (too short reads as low-effort, too
long is hard to say out loud), and does it reference something specific
(a theme or interest) rather than being generic enough to apply to any
event at all.
"""

from typing import List, Tuple

# Generic phrases that could open a conversation about literally anything.
# Their presence is a weak signal that the line didn't really key off the
# event's themes or the user's interests.
_GENERIC_PHRASES = (
    "how's it going",
    "what do you do",
    "nice to meet you",
    "how are you",
    "tell me about yourself",
)

MIN_GOOD_LENGTH = 25
MAX_GOOD_LENGTH = 140


def score_suggestion(suggestion: str, themes: List[str], interests: List[str]) -> Tuple[int, str]:
    """
    Score a single generated suggestion from 1 (weak) to 5 (strong).

    Args:
        suggestion: The generated conversation starter text.
        themes: Themes extracted from the event description, used to check
            whether the suggestion actually references the event context.
        interests: The user's stated interests, used the same way.

    Returns:
        A (score, explanation) tuple. Score is an int 1-5. Explanation is a
        short string describing the dominant reason for the score, intended
        for display directly in the UI next to the suggestion.
    """
    if not suggestion or not suggestion.strip():
        return 1, "empty suggestion"

    text = suggestion.strip()
    lower = text.lower()
    score = 3  # start at a neutral midpoint, then adjust up/down
    reasons: List[str] = []

    # --- Is it phrased as a question? ---
    # A question explicitly invites a reply, which is what an icebreaker
    # is for. A flat statement leaves the other person to supply the next
    # line themselves.
    is_question = text.endswith("?")
    if is_question:
        score += 1
        reasons.append("ends in a question")
    else:
        score -= 1
        reasons.append("phrased as a statement, not a question")

    # --- Does it reference a specific theme or interest? ---
    # Specificity is what separates "what do you do?" from something that
    # could only have been generated for *this* event.
    keywords = [t.lower() for t in themes] + [i.lower() for i in interests]
    mentions_specific = any(kw and kw in lower for kw in keywords)
    if mentions_specific:
        score += 1
        reasons.append("references the event's themes or your interests")
    else:
        reasons.append("doesn't clearly reference a specific theme")

    # --- Is it a recognizable generic opener? ---
    # These work anywhere, which is also their weakness -- they signal the
    # generation didn't really use the context it was given.
    if any(phrase in lower for phrase in _GENERIC_PHRASES):
        score -= 1
        reasons.append("a generic, all-purpose opener")

    # --- Length sanity check ---
    # Too short usually means a fragment cut off mid-thought, or a stray
    # partial line from the model's response. Too
    # long is hard to actually say out loud as a one-line opener.
    length = len(text)
    if length < MIN_GOOD_LENGTH:
        score -= 1
        reasons.append("quite short, may read as a fragment")
    elif length > MAX_GOOD_LENGTH:
        score -= 1
        reasons.append("long for a one-line opener")

    score = max(1, min(5, score))

    # Lead the explanation with whichever reason most directly explains the
    # final score, favoring the specificity/question signals over the
    # length check since those are the stronger predictors of "usable."
    explanation = reasons[0] if reasons else "average opener"
    if len(reasons) > 1:
        explanation = f"{reasons[0]}, {reasons[1]}"

    return score, explanation


def score_suggestions(
    suggestions: List[str], themes: List[str], interests: List[str]
) -> Tuple[List[int], List[str]]:
    """
    Score a full list of suggestions in one call.

    Returns:
        A (scores, explanations) tuple of two parallel lists, same length
        and order as `suggestions`.
    """
    scores: List[int] = []
    explanations: List[str] = []
    for suggestion in suggestions:
        score, explanation = score_suggestion(suggestion, themes, interests)
        scores.append(score)
        explanations.append(explanation)
    return scores, explanations
