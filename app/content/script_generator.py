import re
from html import unescape


# How many summary sentences to keep -- this is a short single-story
# clip, not a full article read-through.
MAX_SUMMARY_SENTENCES = 3


def _strip_html(text: str) -> str:
    # RSS summaries are frequently HTML fragments (<p>, <a>, entities).
    # Strip tags and decode entities so the result reads as plain
    # narration text.
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_sentences(text: str) -> list[str]:
    # Simple sentence splitter: split after ./!/? followed by
    # whitespace. Good enough for RSS summary text -- not meant to
    # handle every edge case (abbreviations, decimals, etc.). A real
    # script-writing LLM pass is future work; this is the
    # deterministic placeholder, same pattern as the AI-relevance
    # filter and dedup engine.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def build_summary(
    raw_summary: str | None,
    max_sentences: int = MAX_SUMMARY_SENTENCES,
) -> str:
    if not raw_summary:
        return "No summary was available from the source."

    cleaned = _strip_html(raw_summary)
    sentences = _split_sentences(cleaned)

    if not sentences:
        return "No summary was available from the source."

    return " ".join(sentences[:max_sentences])


def build_why_it_matters(filter_reason: str | None, source_name: str) -> str:
    # filter_reason comes from the AI-relevance filter and looks like
    # "Matched: ai, openai, gpt" -- reuse those already-computed
    # keywords to build a data-driven one-liner instead of a second
    # free-text generation pass.
    if not filter_reason or ":" not in filter_reason:
        return f"This story was flagged as AI-relevant coverage from {source_name}."

    _, _, keyword_part = filter_reason.partition(":")
    keywords = [k.strip() for k in keyword_part.split(",") if k.strip()]

    if not keywords:
        return f"This story was flagged as AI-relevant coverage from {source_name}."

    keyword_str = ", ".join(keywords[:3])
    return (
        f"This matters because it touches on {keyword_str}, signaling "
        f"where AI development is heading next."
    )


def generate_script(
    title: str,
    raw_summary: str | None,
    filter_reason: str | None,
    source_name: str,
) -> dict:
    """
    Deterministic, template-based script generation -- no LLM call,
    no API key. Same "explainable, data-driven" pattern as the
    AI-relevance filter and dedup engine elsewhere in this codebase.

    Returns headline/summary/why_it_matters separately (for display)
    plus script_text, the full narration string fed to voice
    synthesis.
    """

    headline = title.strip()
    summary = build_summary(raw_summary)
    why_it_matters = build_why_it_matters(filter_reason, source_name)

    script_text = f"{headline}. {summary} {why_it_matters}"
    script_text = re.sub(r"\s+", " ", script_text).strip()

    return {
        "headline": headline,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "script_text": script_text,
    }
