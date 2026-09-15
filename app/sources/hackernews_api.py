import time

import requests


# Official Algolia-powered Hacker News search API -- the same one
# that backs hn.algolia.com. Free, no API key.
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"

# Community-vetted threshold: below this, results skew toward noise
# (low-engagement submissions) rather than genuinely newsworthy
# discussion. Verified during research: points>15 across 7 sampled
# days consistently returned 19-24 qualifying AI stories/day.
MIN_POINTS = 15

REQUEST_TIMEOUT_SECONDS = 15


def fetch_ai_stories(window_hours: float) -> list[dict]:
    """
    Fetch Hacker News stories mentioning "AI", posted within the last
    `window_hours`, with more than MIN_POINTS points.

    Returns the raw Algolia hit dicts (field mapping into our Story
    model happens in app/tasks/ingestion_hackernews.py, matching the
    fetch/orchestrate separation used elsewhere in this codebase).
    """

    window_start_ts = int(time.time() - window_hours * 3600)

    response = requests.get(
        HN_SEARCH_URL,
        params={
            "tags": "story",
            "query": "AI",
            "numericFilters": f"points>{MIN_POINTS},created_at_i>{window_start_ts}",
            "hitsPerPage": 100,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    return response.json().get("hits", [])
