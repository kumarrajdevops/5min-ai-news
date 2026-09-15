from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text

from app.db import SessionLocal
from app.models import Episode, EpisodeStory, Story, StoryContent
from app.tasks.content import generate_script_task
from app.tasks.dedup import deduplicate_new_stories
from app.tasks.ingestion import ingest_news
from app.tasks.ranking import run_ranking_selection


# Object-storage-style local media root (see app/tasks/content.py).
# Created up front so the StaticFiles mount below always has a valid
# directory to serve, even before any content has been generated yet.
MEDIA_ROOT = Path("media")
for _subdir in ("audio", "images", "captions", "videos"):
    (MEDIA_ROOT / _subdir).mkdir(parents=True, exist_ok=True)


app = FastAPI(
    title="AI News Platform",
    version="0.1.0",
    description="Local-first AI technology news pipeline.",
)

# Serves generated audio/images/captions/videos directly, e.g.
# GET /media/videos/15.mp4 -- lets a browser play back a produced
# story's video without a separate file server.
app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")


@app.on_event("startup")
def startup() -> None:
    """
    Verify the database is reachable at startup.

    Schema management belongs entirely to Alembic
    (`alembic upgrade head`) -- this app deliberately does NOT call
    Base.metadata.create_all() here. It used to, and that caused a
    real bug: create_all() builds the full current schema straight
    from the latest models on any fresh database, but Alembic never
    finds out a migration was "applied" that way. A later
    `alembic upgrade head` then tries to re-run migration #1 from
    scratch and fails with DuplicateColumn, because the columns
    already exist. Keeping schema creation solely in Alembic's hands
    avoids that class of bug entirely.

    This still fails loudly and immediately if the database is
    completely unreachable (wrong host/credentials, Postgres not up
    yet) rather than deferring that failure to the first request.
    """
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-news-api"}


@app.post("/api/v1/ingestion/rss")
def trigger_rss_ingestion():
    task = ingest_news.delay()
    return {"task_id": task.id, "status": "queued"}


@app.post("/api/v1/dedup/run")
def trigger_dedup():
    """
    Manually trigger the deduplication pass. Normally this runs
    automatically at the end of every ingestion cycle, but this
    endpoint is useful for testing/verification, or for re-running
    dedup without doing a full ingestion cycle first.
    """
    task = deduplicate_new_stories.delay()
    return {"task_id": task.id, "status": "queued"}


@app.post("/api/v1/episodes/select")
def trigger_ranking_selection(run_date: str | None = None):
    """
    Trigger ranking + Top-25/5-backup selection, creating a new
    Episode. Deliberately NOT auto-chained after ingestion/dedup --
    per the architecture's daily cycle, this should run once, after
    the collection cutoff, not after every ingestion pass.

    run_date: optional "YYYY-MM-DD" override, mainly for testing.
    Defaults to today (UTC date) if omitted.

    Validated here rather than left to the Celery task: the task runs
    out-of-process, so an invalid value would otherwise fail silently
    from the caller's perspective (HTTP 200 + queued task_id, with the
    actual ValueError only visible in the worker logs).
    """
    if run_date is not None:
        try:
            date.fromisoformat(run_date)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid run_date {run_date!r}; expected YYYY-MM-DD.",
            )

    task = run_ranking_selection.delay(run_date)
    return {"task_id": task.id, "status": "queued"}


@app.get("/api/v1/episodes/latest")
def get_latest_episode():
    """
    Convenience endpoint: fetch the most recently created episode
    without needing to know its id.
    """
    with SessionLocal() as db:
        episode = db.scalars(
            select(Episode).order_by(Episode.created_at.desc()).limit(1)
        ).first()

        if episode is None:
            raise HTTPException(status_code=404, detail="No episodes yet.")

        return _serialize_episode(db, episode)


@app.get("/api/v1/episodes/{episode_id}")
def get_episode(episode_id: int):
    with SessionLocal() as db:
        episode = db.get(Episode, episode_id)

        if episode is None:
            raise HTTPException(status_code=404, detail="Episode not found.")

        return _serialize_episode(db, episode)


def _serialize_episode(db, episode: Episode) -> dict:
    """
    Shared serialization for the two episode-viewing endpoints above.
    Splits the selection into primary (Top 25) and backup (next 5)
    lists, each ordered by rank_position, joined against the actual
    story data.
    """

    rows = (
        db.query(EpisodeStory, Story)
        .join(Story, EpisodeStory.story_id == Story.id)
        .filter(EpisodeStory.episode_id == episode.id)
        .order_by(EpisodeStory.rank_position.asc())
        .all()
    )

    primary = []
    backup = []

    for episode_story, story in rows:
        entry = {
            "rank_position": episode_story.rank_position,
            "rank_score": episode_story.rank_score,
            "rank_reason": episode_story.rank_reason,
            "story_id": story.id,
            "title": story.title,
            "url": story.url,
            "source_name": story.source_name,
            "published_at": story.published_at,
        }

        if episode_story.selection_status == "primary":
            primary.append(entry)
        else:
            backup.append(entry)

    return {
        "episode_id": episode.id,
        "run_date": episode.run_date,
        "status": episode.status,
        "created_at": episode.created_at,
        "primary_count": len(primary),
        "backup_count": len(backup),
        "primary": primary,
        "backup": backup,
    }


@app.get("/api/v1/stories")
def list_stories(limit: int = 30):
    # Keep the API limit between 1 and 100.
    limit = max(1, min(limit, 100))

    with SessionLocal() as db:
        stories = db.scalars(
            select(Story)
            # Only expose stories classified as AI candidates.
            .where(Story.ai_relevance == "ai_candidate")
            # Exclude stories that were grouped as duplicates of
            # another story -- only the canonical representative of
            # each duplicate cluster should reach downstream ranking.
            .where(Story.canonical_story_id.is_(None))
            # Show newest published stories first.
            .order_by(Story.published_at.desc())
            # Apply the requested result limit.
            .limit(limit)
        ).all()

        return [
            {
                "id": story.id,
                "title": story.title,
                "url": story.url,
                "source_name": story.source_name,
                "source_type": story.source_type,
                "published_at": story.published_at,
                "collected_at": story.collected_at,
                "status": story.status,
                # Return the filter classification for API consumers.
                "ai_relevance": story.ai_relevance,
                # Return the deterministic relevance score.
                "ai_relevance_score": story.ai_relevance_score,
                # Return why the filter classified the story this way.
                "filter_reason": story.filter_reason,
            }
            for story in stories
        ]


@app.post("/api/v1/stories/{story_id}/produce")
def trigger_content_production(story_id: int):
    """
    Kick off the full script -> voice -> visual -> video pipeline for
    a single story (see app/tasks/content.py). Each stage chains into
    the next via .delay(); poll GET /api/v1/stories/{id}/content for
    progress.

    Deliberately scoped to one story at a time for now -- this proves
    out the architecture's Script/Voice/Visual/Video stages end to
    end before wiring them up to run across an entire Top-25 episode.
    """
    with SessionLocal() as db:
        story = db.get(Story, story_id)

        if story is None:
            raise HTTPException(status_code=404, detail="Story not found.")

    task = generate_script_task.delay(story_id)
    return {"story_id": story_id, "task_id": task.id, "status": "queued"}


@app.get("/api/v1/stories/{story_id}/content")
def get_story_content(story_id: int):
    """
    Fetch the generated production artifacts for a story: script
    text, and URLs for the audio/image/captions/video files once
    each stage has completed. `status` tracks progress through the
    pipeline (pending -> script_ready -> voice_ready -> visual_ready
    -> video_ready, or failed -- see error_message).
    """
    with SessionLocal() as db:
        content = (
            db.query(StoryContent)
            .filter(StoryContent.story_id == story_id)
            .first()
        )

        if content is None:
            raise HTTPException(
                status_code=404,
                detail="No content generated for this story yet.",
            )

        def media_url(path: str | None) -> str | None:
            # Stored paths already look like "media/audio/15.mp3",
            # matching the /media StaticFiles mount above.
            return f"/{path}" if path else None

        return {
            "story_id": content.story_id,
            "status": content.status,
            "headline": content.headline,
            "summary": content.summary,
            "script_text": content.script_text,
            "audio_url": media_url(content.audio_path),
            "audio_duration_seconds": content.audio_duration_seconds,
            "image_url": media_url(content.image_path),
            "captions_url": media_url(content.captions_path),
            "video_url": media_url(content.video_path),
            "error_message": content.error_message,
            "created_at": content.created_at,
            "updated_at": content.updated_at,
        }


@app.get("/api/v1/stories/{story_id}/duplicates")
def list_duplicates(story_id: int):
    """
    List every story that was grouped as a duplicate of the given
    canonical story. Useful for verifying dedup behavior and for a
    future editorial dashboard ("this story also covered by: ...").
    """

    with SessionLocal() as db:
        duplicates = db.scalars(
            select(Story)
            .where(Story.canonical_story_id == story_id)
            .order_by(Story.published_at.asc())
        ).all()

        return [
            {
                "id": story.id,
                "title": story.title,
                "url": story.url,
                "source_name": story.source_name,
                "published_at": story.published_at,
                "dedup_reason": story.dedup_reason,
            }
            for story in duplicates
        ]