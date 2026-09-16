from app.content.script_generator import build_summary, generate_script


def test_no_summary_falls_back_to_placeholder():
    assert build_summary(None) == "No summary was available from the source."
    assert build_summary("") == "No summary was available from the source."


def test_strips_html_tags_and_entities():
    summary = build_summary("<p>OpenAI &amp; friends ship a model.</p>")
    assert "<p>" not in summary
    assert "&amp;" not in summary
    assert "OpenAI & friends ship a model." in summary


def test_truncation_marker_is_dropped():
    """
    Regression for the "summary trails off mid-thought" bug: a feed's
    own excerpt-cutoff ellipsis must not be read aloud as if it were a
    complete sentence.
    """
    summary = build_summary(
        "The company announced a new product. It will ship next year. "
        "The team is also signing on to a […]"
    )
    assert "[…]" not in summary
    assert summary.endswith("It will ship next year.")


def test_promo_sentence_is_dropped():
    """
    Regression for the "sign up here" bug found via live audit this
    session -- a newsletter-pitch sentence must not appear in the
    narrated summary.
    """
    summary = build_summary(
        "This weekend, Dario Amodei posted an essay calling for a brake "
        "on AI development. To get stories like this in your inbox "
        "first, sign up here."
    )
    assert "sign up" not in summary.lower()
    assert "Dario Amodei" in summary


def test_promo_sentence_variants_all_dropped():
    for phrase in [
        "Subscribe to our YouTube channel for more videos.",
        "Log in to read the rest of this article.",
        "Sign in with your account to continue.",
        "Check out our newsletter for weekly updates.",
    ]:
        summary = build_summary(f"Real content here. {phrase}")
        assert phrase not in summary
        assert "Real content here." in summary


def test_all_sentences_promotional_falls_back_to_placeholder():
    """
    If filtering out promo sentences leaves nothing real (the story
    #39 case from this session's audit -- the entire fetched page was
    a subscription pitch), the honest "no summary" fallback is correct,
    not an empty string.
    """
    summary = build_summary("Subscribe to my premium newsletter for $70 a year.")
    assert summary == "No summary was available from the source."


def test_summary_truncates_to_max_sentences():
    raw = "One. Two. Three. Four. Five."
    summary = build_summary(raw, max_sentences=2)
    assert summary == "One. Two."


def test_generate_script_combines_headline_and_summary():
    result = generate_script(title="  Big AI News  ", raw_summary="Something happened.")
    assert result["headline"] == "Big AI News"
    assert result["summary"] == "Something happened."
    assert result["script_text"] == "Big AI News. Something happened."


def test_generate_script_normalizes_whitespace():
    result = generate_script(title="Title", raw_summary="Line one.\n\nLine  two.")
    assert "\n" not in result["script_text"]
    assert "  " not in result["script_text"]
