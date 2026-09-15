import re


# AI terms that are strong enough to identify an AI-related story.
# These are intentionally specific technology/company/model terms.
AI_KEYWORDS = {
    "ai",
    "artificial intelligence",
    "machine learning",
    "generative ai",
    "generative artificial intelligence",
    "large language model",
    "large language models",
    "llm",
    "llms",
    "ai model",
    "ai models",
    "foundation model",
    "foundation models",
    "neural network",
    "deep learning",
    "openai",
    "anthropic",
    "google deepmind",
    "google ai",
    "gemini",
    "gpt",
    "claude",
    "llama",
    "mistral",
    "deepseek",
    "hugging face",
    "nvidia ai",
    "ai agent",
    "ai agents",
    "agentic ai",
    "computer vision",
    "robotics",
    "multimodal",
    "reasoning model",
    "reasoning models",
}


def find_matches(text: str) -> list[str]:
    # Find AI technology terms using whole-word matching.
    matched_keywords = []

    # Normalize the text before searching.
    text = text.lower()

    # Check every configured AI keyword.
    for keyword in AI_KEYWORDS:

        # Build a regex that matches the complete keyword.
        pattern = r"\b" + re.escape(keyword) + r"\b"

        # Add the keyword when it appears in the text.
        if re.search(pattern, text):
            matched_keywords.append(keyword)

    # Return all matching AI terms.
    return matched_keywords


def calculate_ai_relevance(
    title: str,
    summary: str | None,
) -> tuple[str, float, str]:
    """
    Basic deterministic AI relevance filter.

    Strategy:
        1. Search the title for AI technology terms.
        2. Search the summary only for stronger supporting terms.
        3. A generic standalone "AI" mention in the summary is not enough.
    """

    # Normalize the title.
    title_text = title.lower()

    # Normalize the summary.
    summary_text = (summary or "").lower()

    # ---------------------------------------------------------
    # TITLE MATCHING
    # ---------------------------------------------------------

    # First check the title because it is the strongest signal
    # for determining what the article is actually about.
    title_matches = find_matches(title_text)

    # ---------------------------------------------------------
    # SUMMARY MATCHING
    # ---------------------------------------------------------

    # Check the summary for supporting AI technology terms.
    summary_matches = find_matches(summary_text)

    # Remove duplicate terms already found in the title.
    summary_only_matches = [
        keyword
        for keyword in summary_matches
        if keyword not in title_matches
    ]

    # ---------------------------------------------------------
    # DECISION
    # ---------------------------------------------------------

    # If the title contains an AI technology term, classify it
    # as an AI candidate.
    if title_matches:

        # Start with a base score for a strong title match.
        score = 0.5

        # Increase the score for additional AI terms.
        score += len(title_matches) * 0.1

        # Cap the score at 1.0.
        score = min(1.0, score)

        # Include supporting summary terms in the explanation.
        all_matches = title_matches + summary_only_matches

        # Return the AI classification.
        return (
            "ai_candidate",
            score,
            f"Matched: {', '.join(all_matches[:10])}",
        )

    # ---------------------------------------------------------
    # SUMMARY-ONLY MATCHING
    # ---------------------------------------------------------

    # A summary-only match must be a strong AI technology term.
    # A generic "AI" mention alone is intentionally NOT enough.
    strong_summary_matches = [
        keyword
        for keyword in summary_only_matches
        if keyword != "ai"
    ]

    # If strong AI terminology appears in the summary,
    # classify the article as an AI candidate.
    if strong_summary_matches:

        # Use a slightly lower score because the title itself
        # did not explicitly identify the article as AI-related.
        score = 0.4

        # Add a small amount for multiple strong matches.
        score += min(
            0.3,
            (len(strong_summary_matches) - 1) * 0.1,
        )

        # Cap the score at 1.0.
        score = min(1.0, score)

        # Return the AI classification.
        return (
            "ai_candidate",
            score,
            f"Matched in summary: "
            f"{', '.join(strong_summary_matches[:10])}",
        )

    # ---------------------------------------------------------
    # NOT AI
    # ---------------------------------------------------------

    # No meaningful AI technology terminology was found.
    return (
        "not_ai",
        0.0,
        "No AI technology terms detected.",
    )
