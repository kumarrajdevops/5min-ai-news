from app.filters.ai_relevance import calculate_ai_relevance


def test_title_with_ai_term_is_candidate():
    relevance, score, reason = calculate_ai_relevance(
        title="OpenAI releases new model",
        summary="Some general summary text.",
    )
    assert relevance == "ai_candidate"
    assert score >= 0.5
    assert "openai" in reason.lower()


def test_multiple_title_terms_increase_score():
    _, score_one, _ = calculate_ai_relevance(
        title="OpenAI ships a new model",
        summary=None,
    )
    _, score_many, _ = calculate_ai_relevance(
        title="OpenAI's new large language model uses deep learning",
        summary=None,
    )
    assert score_many > score_one


def test_score_never_exceeds_one():
    _, score, _ = calculate_ai_relevance(
        title="AI artificial intelligence machine learning generative ai "
        "large language model llm ai model foundation model neural network "
        "deep learning openai anthropic google deepmind",
        summary=None,
    )
    assert score <= 1.0


def test_strong_summary_only_match_is_candidate():
    relevance, score, reason = calculate_ai_relevance(
        title="Company announces quarterly earnings",
        summary="The report was generated using a large language model.",
    )
    assert relevance == "ai_candidate"
    assert "large language model" in reason.lower()


def test_generic_ai_mention_in_summary_alone_is_not_enough():
    """
    A bare "AI" mention in the summary (no stronger term, and no AI
    term in the title at all) is deliberately not enough on its own --
    see the docstring on calculate_ai_relevance for why.
    """
    relevance, _, _ = calculate_ai_relevance(
        title="Company announces quarterly earnings",
        summary="Some analysts used AI to review the numbers.",
    )
    assert relevance == "not_ai"


def test_unrelated_story_is_not_ai():
    relevance, score, _ = calculate_ai_relevance(
        title="Local team wins championship game",
        summary="A thrilling overtime victory capped off the season.",
    )
    assert relevance == "not_ai"
    assert score == 0.0


def test_no_summary_does_not_crash():
    relevance, _, _ = calculate_ai_relevance(title="Some headline", summary=None)
    assert relevance == "not_ai"


def test_matching_is_case_insensitive():
    relevance, _, _ = calculate_ai_relevance(title="OPENAI ships GPT", summary=None)
    assert relevance == "ai_candidate"


def test_word_boundary_avoids_false_positive_substring():
    """
    "ai" must match as a whole word, not as a substring of an
    unrelated word (e.g. "email", "captain", "explain").
    """
    relevance, _, _ = calculate_ai_relevance(
        title="Explain the plan to the captain",
        summary="Details in the email.",
    )
    assert relevance == "not_ai"
