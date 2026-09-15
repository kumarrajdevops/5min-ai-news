from urllib.parse import urlparse


# Curated display names for outlets already confirmed present in real
# ingested data. "news.ycombinator.com" -> "Hacker News" is what makes
# self-posts (Ask/Show/Tell HN, which fall back to the HN permalink)
# resolve correctly automatically, with no special-casing needed by
# callers -- every Hacker News item's final URL, real external link or
# permalink fallback alike, just passes through this one function.
KNOWN_PUBLISHERS: dict[str, str] = {
    "news.ycombinator.com": "Hacker News",
    "theguardian.com": "The Guardian",
    "theregister.com": "The Register",
    "macrumors.com": "MacRumors",
    "spectrum.ieee.org": "IEEE Spectrum",
}


def resolve_publisher(url: str) -> str:
    """
    Resolve the actual publisher of a URL from its hostname.

    For outlets we've curated (see KNOWN_PUBLISHERS), returns the real
    display name. For everything else, falls back to a cleaned-up
    version of the raw hostname -- honest and conservative rather than
    guessing at a "real" name for a site we haven't vetted.
    """

    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower()

    if hostname.startswith("www."):
        hostname = hostname[len("www."):]

    if hostname in KNOWN_PUBLISHERS:
        return KNOWN_PUBLISHERS[hostname]

    # Title-casing an arbitrary hostname produces awkward results
    # (e.g. "sunkcost.ai" -> "Sunkcost.Ai") since it capitalizes after
    # every "." too -- just return the raw hostname unchanged instead.
    return hostname if hostname else "Unknown"
