from app.sources.publisher_resolver import resolve_publisher


def test_known_publisher_resolves_to_curated_name():
    assert resolve_publisher("https://www.theguardian.com/some/article") == "The Guardian"


def test_hacker_news_self_post_resolves_to_hacker_news():
    """
    Ask/Show/Tell HN self-posts fall back to the HN permalink as their
    url -- this is what makes them correctly resolve to "Hacker News"
    itself, with no special-casing needed by callers.
    """
    assert resolve_publisher("https://news.ycombinator.com/item?id=123") == "Hacker News"


def test_www_prefix_is_stripped_before_lookup():
    assert resolve_publisher("https://www.macrumors.com/2026/01/01/story/") == "MacRumors"


def test_unknown_publisher_falls_back_to_raw_hostname():
    assert resolve_publisher("https://sunkcost.ai/post") == "sunkcost.ai"


def test_unknown_publisher_hostname_is_lowercased():
    assert resolve_publisher("https://SunkCost.AI/post") == "sunkcost.ai"


def test_malformed_url_falls_back_to_unknown():
    assert resolve_publisher("not a url") == "Unknown"
