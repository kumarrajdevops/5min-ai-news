from datetime import datetime, timedelta, timezone  # Date/time handling

import feedparser  # Read and parse RSS feeds
from dateutil import parser as date_parser  # Robust date parsing (RFC 2822 + ISO 8601 + more)

from app.config import settings  # Application configuration
from app.db import SessionLocal  # PostgreSQL database session
from app.filters.ai_relevance import calculate_ai_relevance  # AI relevance filter
from app.models import Story  # Story database model
from app.sources.registry import NEWS_SOURCES  # Configured news sources
from app.tasks.dedup import deduplicate_new_stories  # Duplicate-story grouping
from app.worker.celery_app import celery_app  # Celery application


# Many sites (VentureBeat's Vercel bot-challenge is a known example) block
# or throttle requests that don't look like they come from a browser.
# feedparser does not send one by default, so we set one explicitly.
FEED_USER_AGENT = (
    "Mozilla/5.0 (compatible; AINewsPlatformBot/1.0; "
    "+https://github.com/5min-ai-news)"
)


def parse_published(value: str | None) -> datetime | None:
    """
    Convert RSS publication date into a timezone-aware UTC datetime.

    Feeds are inconsistent about date format: some use RFC 2822
    ("Wed, 09 Sep 2026 17:42:19 -0400"), others use ISO 8601
    ("2026-09-09T17:42:19-04:00"). dateutil.parser.parse() handles
    both (and most other common variants), unlike email.utils'
    parsedate_to_datetime which only understands RFC 2822.
    """

    if not value:  # RSS entry has no publication date
        return None

    try:
        dt = date_parser.parse(value)  # Handles RFC 2822, ISO 8601, and more

        if dt.tzinfo is None:  # If RSS date has no timezone information
            dt = dt.replace(tzinfo=timezone.utc)  # Treat it as UTC

        return dt.astimezone(timezone.utc)  # Normalize everything to UTC

    except (TypeError, ValueError, OverflowError):  # Invalid/unparseable date
        return None


@celery_app.task  # Register this function as a Celery background task
def ingest_news() -> dict:
    """
    Fetch enabled RSS sources and store new stories.
    """

    # ---------------------------------------------------------
    # Ingestion statistics
    # ---------------------------------------------------------

    sources_processed = 0  # Number of enabled sources processed
    articles_seen = 0  # Total RSS articles encountered
    articles_inserted = 0  # New stories inserted into PostgreSQL
    duplicates = 0  # Existing stories skipped
    invalid = 0  # Articles missing required/valid data
    outside_window = 0  # Articles older than our news window
    failed_sources = 0  # Sources that failed during processing

    # Per-source breakdown, so we can see which sources actually
    # contributed stories vs. which ones look "processed" but yielded
    # nothing (blocked, empty, or malformed).
    per_source_stats: dict[str, dict[str, int]] = {}

    # ---------------------------------------------------------
    # Define the current news collection window
    # ---------------------------------------------------------

    now = datetime.now(timezone.utc)  # Current UTC time

    window_start = now - timedelta(
        hours=settings.news_window_hours  # Only accept recent articles
    )

    # ---------------------------------------------------------
    # Open PostgreSQL database session
    # ---------------------------------------------------------

    with SessionLocal() as db:

        # -----------------------------------------------------
        # Process every enabled source
        # -----------------------------------------------------

        for source in NEWS_SOURCES:

            if not source["enabled"]:  # Skip disabled sources
                continue

            sources_processed += 1  # Count this source

            source_seen = 0
            source_inserted = 0
            source_duplicates = 0
            source_invalid = 0
            source_outside_window = 0

            try:
                # -------------------------------------------------
                # Download and parse the RSS feed
                # -------------------------------------------------

                feed = feedparser.parse(
                    source["url"],  # RSS URL from source registry
                    agent=FEED_USER_AGENT,  # Look like a real browser/bot, not default urllib
                )

                # -------------------------------------------------
                # Surface transport-level problems feedparser doesn't
                # raise as exceptions (HTTP errors, malformed XML).
                # feedparser sets `status` for HTTP fetches and `bozo`
                # when the feed body itself failed to parse cleanly.
                # -------------------------------------------------

                http_status = getattr(feed, "status", None)

                if http_status is not None and http_status >= 400:
                    print(
                        f"[{source['name']}] HTTP {http_status} fetching feed "
                        f"— 0 entries will be available even though this "
                        f"is not counted as a failed_source."
                    )

                if getattr(feed, "bozo", 0):
                    bozo_exc = getattr(feed, "bozo_exception", None)
                    print(
                        f"[{source['name']}] Feed parsed with warnings "
                        f"(bozo=1): {bozo_exc}"
                    )

                print(
                    f"[{source['name']}] HTTP status={http_status}, "
                    f"entries found={len(feed.entries)}"
                )

                # -------------------------------------------------
                # Process every article in the feed
                # -------------------------------------------------

                for entry in feed.entries:

                    articles_seen += 1  # Count this article
                    source_seen += 1

                    # Extract article title
                    title = getattr(
                        entry,
                        "title",
                        None,
                    )

                    # Extract article URL
                    url = getattr(
                        entry,
                        "link",
                        None,
                    )

                    # -------------------------------------------------
                    # Validate required fields
                    # -------------------------------------------------

                    if not title or not url:
                        invalid += 1  # Article cannot be stored
                        source_invalid += 1
                        print(
                            f"[{source['name']}] REJECTED (invalid): "
                            f"missing title or url. "
                            f"title={title!r} url={url!r}"
                        )
                        continue

                    # -------------------------------------------------
                    # Check whether this URL already exists
                    # -------------------------------------------------

                    existing_story = (
                        db.query(Story)
                        .filter(Story.url == url)
                        .first()
                    )

                    if existing_story:
                        duplicates += 1  # Skip already collected story
                        source_duplicates += 1
                        continue

                    # -------------------------------------------------
                    # Extract publication date
                    # -------------------------------------------------

                    published_value = (
                        getattr(entry, "published", None)
                        or getattr(entry, "updated", None)
                    )

                    published_at = parse_published(
                        published_value
                    )

                    # -------------------------------------------------
                    # Reject articles without a valid publication date
                    # -------------------------------------------------

                    if published_at is None:
                        invalid += 1
                        source_invalid += 1
                        print(
                            f"[{source['name']}] REJECTED (invalid): "
                            f"unparseable publish date. "
                            f"raw_value={published_value!r} title={title!r}"
                        )
                        continue

                    # -------------------------------------------------
                    # Reject articles outside our configured time window
                    # -------------------------------------------------

                    if published_at < window_start:
                        outside_window += 1
                        source_outside_window += 1
                        continue

                    # -------------------------------------------------
                    # Extract optional RSS fields
                    # -------------------------------------------------

                    author = getattr(
                        entry,
                        "author",
                        None,
                    )

                    summary = getattr(
                        entry,
                        "summary",
                        None,
                    )

                    external_id = getattr(
                        entry,
                        "id",
                        None,
                    )

                    # -------------------------------------------------
                    # Run deterministic AI relevance filter
                    # -------------------------------------------------

                    ai_relevance, ai_score, filter_reason = (
                        calculate_ai_relevance(
                            title=title,
                            summary=summary,
                        )
                    )

                    # -------------------------------------------------
                    # Create database Story object
                    # -------------------------------------------------

                    story = Story(
                        title=title.strip(),  # Clean article title
                        url=url.strip(),  # Clean article URL
                        source_name=source["name"],  # Source name
                        source_type=source["source_type"],  # RSS
                        published_at=published_at,  # Original publication time
                        author=author,  # Article author if available
                        external_id=external_id,  # Source-provided ID
                        raw_summary=summary,  # Original RSS summary
                        collected_at=datetime.now(timezone.utc),  # Collection time
                        status="collected",  # Initial pipeline status

                        # AI relevance classification
                        ai_relevance=ai_relevance,

                        # Relevance score generated by our deterministic filter
                        ai_relevance_score=ai_score,

                        # Explanation for why the filter classified it this way
                        filter_reason=filter_reason,
                    )

                    # Add the new story to the current database transaction
                    db.add(story)

                    # Count the article as inserted
                    articles_inserted += 1
                    source_inserted += 1

                # -------------------------------------------------
                # Commit all stories from this source
                # -------------------------------------------------

                db.commit()

                per_source_stats[source["name"]] = {
                    "seen": source_seen,
                    "inserted": source_inserted,
                    "duplicates": source_duplicates,
                    "invalid": source_invalid,
                    "outside_window": source_outside_window,
                }

            except Exception as exc:

                # Roll back failed database transaction
                db.rollback()

                failed_sources += 1  # Record source failure

                per_source_stats[source["name"]] = {"error": str(exc)}

                print(
                    f"Failed to process "
                    f"{source['name']}: {exc}"
                )

    # ---------------------------------------------------------
    # Print a clear per-source breakdown so it's obvious at a glance
    # which sources are actually contributing stories.
    # ---------------------------------------------------------

    print("---- Per-source ingestion breakdown ----")
    for name, stats in per_source_stats.items():
        print(f"  {name}: {stats}")
    print("-----------------------------------------")

    # ---------------------------------------------------------
    # Chain into deduplication.
    #
    # Fire-and-forget: we queue the dedup task rather than running it
    # inline, so a slow/failed dedup pass doesn't block ingestion from
    # returning its own result. This matches the ephemeral-compute
    # principle from the architecture -- ingestion and dedup are
    # separate jobs, not one long-running process.
    # ---------------------------------------------------------

    dedup_task = deduplicate_new_stories.delay()

    print(f"[ingestion] Queued dedup task {dedup_task.id}")

    # ---------------------------------------------------------
    # Return ingestion statistics
    # ---------------------------------------------------------

    return {
        "sources_processed": sources_processed,
        "articles_seen": articles_seen,
        "articles_inserted": articles_inserted,
        "duplicates": duplicates,
        "outside_window": outside_window,
        "invalid": invalid,
        "failed_sources": failed_sources,
        "per_source": per_source_stats,
        "dedup_task_id": dedup_task.id,
    }
