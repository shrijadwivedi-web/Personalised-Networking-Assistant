"""
Theme Extraction Benchmark
-----------------------------
A small, informal accuracy check for app.services.event_analyzer's
zero-shot theme extraction. Not a rigorous ML evaluation (15 hand-picked
examples is far too small a sample for a real accuracy claim) -- the goal
is a quick, honest sanity check of the kind that's easy to defend in a
report: "here's 15 examples, here's what the model actually returned, here
is how often the top predicted theme matched what a human would expect."

Usage:
    python scripts/benchmark_theme_extraction.py

Prints a markdown table to stdout, which can be pasted directly into the
README's Model Evaluation section.
"""

from app.services.event_analyzer import extract_event_themes

# Each tuple is (event description, expected top theme). "Expected" here
# means "the theme a human reading this description would name first" --
# a judgment call, not ground truth from a labeled dataset.
TEST_CASES = [
    ("A conference on using AI to design smarter, more sustainable cities.", "artificial intelligence"),
    ("A meetup for people building blockchain-based payment systems.", "blockchain"),
    ("A summit on the future of hospital record-keeping and patient data.", "healthcare"),
    ("An event exploring how universities are adapting to online-first learning.", "education"),
    ("A panel on reducing carbon emissions in the shipping industry.", "climate change"),
    ("A workshop for founders raising their first round of funding.", "entrepreneurship"),
    ("A talk on defending small businesses against ransomware attacks.", "cybersecurity"),
    ("A discussion on solar and wind power replacing fossil fuels.", "sustainability"),
    ("A networking night for people working in venture capital and banking.", "finance"),
    ("A community day about redesigning public transit in growing cities.", "urban planning"),
    ("A hackathon building diagnostic tools for rural clinics.", "healthcare"),
    ("A pitch night for early-stage climate tech startups.", "climate change"),
    ("A seminar on using zero-knowledge proofs in decentralized finance.", "blockchain"),
    ("A career fair for students entering the cybersecurity field.", "cybersecurity"),
    ("A talk on personalized learning powered by machine learning.", "artificial intelligence"),
]


def run_benchmark() -> None:
    correct = 0
    rows = []

    for description, expected in TEST_CASES:
        themes = extract_event_themes(description)
        predicted = themes[0] if themes else "(none)"
        is_match = predicted == expected
        correct += int(is_match)
        rows.append((description, expected, predicted, "✅" if is_match else "❌"))

    print("| Event description | Expected theme | Top predicted theme | Match |")
    print("|---|---|---|---|")
    for description, expected, predicted, mark in rows:
        short_description = description if len(description) <= 60 else description[:57] + "..."
        print(f"| {short_description} | {expected} | {predicted} | {mark} |")

    print()
    print(f"**Top-1 accuracy: {correct}/{len(TEST_CASES)} ({100 * correct / len(TEST_CASES):.0f}%)**")


if __name__ == "__main__":
    run_benchmark()
