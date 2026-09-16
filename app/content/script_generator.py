import re
from html import unescape


# How many summary sentences to keep -- this is a short single-story
# clip, not a full article read-through.
MAX_SUMMARY_SENTENCES = 3

# RSS feeds frequently truncate their excerpt and mark the cut with a
# trailing ellipsis, often bracketed (e.g. "...signing on to a
# [&#8230;]", which unescapes to "...signing on to a […]"). That
# "sentence" is the source's own excerpt cutoff, not a complete
# thought -- keeping it produces a summary that trails off mid-idea.
TRUNCATION_MARKER_RE = re.compile(r"[\[\(]?\s*(?:\.\.\.|…)\s*[\]\)]?\s*$")

# Some feeds' excerpts mix a newsletter/subscription pitch in with the
# actual story text (e.g. "To get stories like this in your inbox
# first, sign up here." or "Subscribe to the MacRumors YouTube channel
# for more videos.") -- drop any sentence that's clearly a promotional
# call-to-action rather than real story content, same rationale as
# TRUNCATION_MARKER_RE above.
PROMO_SENTENCE_RE = re.compile(
    r"\b(sign up|sign in|subscribe|newsletter|log in)\b", re.IGNORECASE
)


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

    # Drop a trailing truncated fragment (the source's own excerpt
    # cutoff) rather than read it aloud mid-thought.
    if sentences and TRUNCATION_MARKER_RE.search(sentences[-1]):
        sentences = sentences[:-1]

    # Drop promotional/newsletter-pitch sentences before truncating to
    # max_sentences, so a promo line doesn't crowd out real content.
    sentences = [s for s in sentences if not PROMO_SENTENCE_RE.search(s)]

    if not sentences:
        return "No summary was available from the source."

    return " ".join(sentences[:max_sentences])


def generate_script(title: str, raw_summary: str | None) -> dict:
    """
    Deterministic, template-based script generation -- no LLM call,
    no API key. Same "explainable, data-driven" pattern as the
    AI-relevance filter and dedup engine elsewhere in this codebase.

    Reads the headline plus a deterministic summary of the story --
    nothing more. No editorializing, no speculative commentary about
    why a story matters or where AI is "heading next".
    """

    headline = title.strip()
    summary = build_summary(raw_summary)

    script_text = f"{headline}. {summary}"
    script_text = re.sub(r"\s+", " ", script_text).strip()

    return {
        "headline": headline,
        "summary": summary,
        "script_text": script_text,
    }
