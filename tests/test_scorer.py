"""
Tests for app.services.scorer.

Uses hand-constructed suggestion strings (rather than real model output)
so each test isolates one specific heuristic, matching the same rationale
given in test_topic_generator.py for why these tests check structure and
specific properties rather than exact scores.
"""

from app.services.scorer import score_suggestion, score_suggestions


def test_question_scores_higher_than_equivalent_statement():
    themes = ["artificial intelligence"]
    interests = ["climate change"]

    question_score, _ = score_suggestion(
        "What do you think about artificial intelligence for climate change?",
        themes,
        interests,
    )
    statement_score, _ = score_suggestion(
        "Artificial intelligence for climate change is happening.", themes, interests
    )
    assert question_score >= statement_score


def test_specific_reference_scores_higher_than_generic_opener():
    themes = ["blockchain"]
    interests = ["finance"]

    specific_score, _ = score_suggestion(
        "How do you see blockchain shaping the future of finance?", themes, interests
    )
    generic_score, _ = score_suggestion("How's it going?", themes, interests)
    assert specific_score > generic_score


def test_empty_suggestion_returns_minimum_score():
    score, explanation = score_suggestion("", ["AI"], ["climate change"])
    assert score == 1
    assert "empty" in explanation


def test_score_is_always_within_valid_range():
    # Deliberately worst-case: generic, non-question, empty-themes context.
    score, _ = score_suggestion("How's it going?", [], [])
    assert 1 <= score <= 5


def test_score_suggestions_returns_parallel_lists():
    suggestions = ["What excites you about AI?", "How's it going?"]
    scores, explanations = score_suggestions(suggestions, ["AI"], ["technology"])
    assert len(scores) == len(suggestions)
    assert len(explanations) == len(suggestions)
    for score in scores:
        assert isinstance(score, int)
        assert 1 <= score <= 5
