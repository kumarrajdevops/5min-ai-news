from datetime import datetime, timezone  # Date/time handling

from dateutil import parser as date_parser  # Robust ISO 8601 date parsing

from app.config import settings  # Application configuration
from app.db import SessionLocal  # PostgreSQL database session
from app.filters.ai_relevance import calculate_ai_relevance  # AI relevance filter
from app.models import Story  # Story database model
from app.sources.hackernews_api import fetch_ai_stories  # Hacker News fetcher
from app.sources.publisher_resolver import resolve_publisher  # Real publisher from URL
from app.tasks.dedup import deduplicate_new_stories  # Duplicate-story grouping
from app.worker.celery_app import celery_app  # Celery application


SOURCE_NAME = "Hacker News"


def parse_published(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        dt = date_parser.parse(value)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except (TypeError, ValueError, OverflowError):
        return None


def _build_url(hit: dict) -> str | None:
    # Link posts have a real external url. Ask/Show/Tell HN self-posts
    # don't -- fall back to the HN discussion permalink so every story
    # still has a usable, unique url.
    url = hit.get("url")
    if url:
        return url

    object_id = hit.get("objectID")
    if object_id:
        return f"https://news.ycombinator.com/item?id={object_id}"

    return None


def _build_summary(hit: dict) -> str:
    story_text = hit.get("story_text")
    if story_text:
        return story_text

    points = hit.get("points", 0)
    num_comments = hit.get("num_comments", 0)
    return f"{points} points, {num_comments} comments on Hacker News."


@celery_app.task
def ingest_hackernews_stories() -> dict:
    """
    Fetch AI-related Hacker News stories and store new ones.

    Same shape as app.tasks.ingestion.ingest_news(): fetch, validate,
    filter, insert, then chain into deduplication. HN's own full-text
    search is a blunter AI-relevance signal than a curated tag would
    be, so stories still run through the same calculate_ai_relevance()
    filter used for RSS sources, rather than being trusted directly.
    """

    seen = 0
    inserted = 0
    duplicates = 0
    invalid = 0

    with SessionLocal() as db:
        try:
            hits = fetch_ai_stories(window_hours=settings.news_window_hours)
        except Exception as exc:
            print(f"[{SOURCE_NAME}] Failed to fetch: {exc}")
            return {"error": str(exc)}

        for hit in hits:
            seen += 1

            title = hit.get("title")
            url = _build_url(hit)

            if not title or not url:
                invalid += 1
                continue

            existing_story = db.query(Story).filter(Story.url == url).first()

            if existing_story:
                duplicates += 1
                continue

            published_at = parse_published(hit.get("created_at"))

            if published_at is None:
                invalid += 1
                continue

            summary = _build_summary(hit)

            ai_relevance, ai_score, filter_reason = calculate_ai_relevance(
                title=title,
                summary=summary,
            )

            story = Story(
                title=title.strip(),
                url=url.strip(),
                # source_name is the actual publisher (resolved from
                # the URL's domain -- e.g. "The Guardian" for a link
                # post, or "Hacker News" itself for a genuine
                # Ask/Show/Tell HN self-post). source_type stays
                # "hackernews" as the discovery-channel marker.
                source_name=resolve_publisher(url),
                source_type="hackernews",
                published_at=published_at,
                author=hit.get("author"),
                external_id=hit.get("objectID"),
                raw_summary=summary,
                collected_at=datetime.now(timezone.utc),
                status="collected",
                ai_relevance=ai_relevance,
                ai_relevance_score=ai_score,
                filter_reason=filter_reason,
            )

            db.add(story)
            inserted += 1

        db.commit()

    result = {
        "seen": seen,
        "inserted": inserted,
        "duplicates": duplicates,
        "invalid": invalid,
    }

    print(f"[{SOURCE_NAME}] {result}")

    dedup_task = deduplicate_new_stories.delay()
    print(f"[{SOURCE_NAME}] Queued dedup task {dedup_task.id}")
    result["dedup_task_id"] = dedup_task.id

    return result
