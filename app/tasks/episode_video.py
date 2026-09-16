from pathlib import Path

from app.content.script_generator import generate_script
from app.content.video_composer import (
    build_captions,
    compose_video,
    concat_videos,
    get_audio_duration_seconds,
)
from app.content.visual_generator import generate_card
from app.content.voice_generator import synthesize_voice
from app.db import SessionLocal
from app.models import Episode, EpisodeStory, Story, StoryContent
from app.tasks.content import MEDIA_ROOT, get_or_create_content, mark_content_failed
from app.worker.celery_app import celery_app


def _produce_story_content(db, story: Story, content: StoryContent) -> bool:
    """
    Run a single story through all four content stages, synchronously
    and in-process (not via the Celery task chain in app/tasks/content.py
    -- those auto-chain the next stage with .delay(), which would run
    async and break the sequential-per-story loop this task needs).
    Reuses the same pure generation functions and the same
    get_or_create_content/mark_content_failed helpers, so behavior
    matches the single-story pipeline exactly; only the orchestration
    (synchronous vs. Celery-chained) differs.

    Returns True if the story reached video_ready, False if any stage
    failed (that story is then skipped from the final concatenation,
    not allowed to block the rest of the episode).
    """

    try:
        script = generate_script(title=story.title, raw_summary=story.raw_summary)
        content.headline = script["headline"]
        content.summary = script["summary"]
        content.script_text = script["script_text"]
        content.status = "script_ready"
        content.error_message = None
        db.commit()
    except Exception as exc:
        mark_content_failed(db, content, "script", exc)
        return False

    try:
        audio_path = MEDIA_ROOT / "audio" / f"{story.id}.mp3"
        synthesize_voice(content.script_text, audio_path)
        content.audio_path = str(audio_path)
        content.audio_duration_seconds = get_audio_duration_seconds(audio_path)
        content.status = "voice_ready"
        content.error_message = None
        db.commit()
    except Exception as exc:
        mark_content_failed(db, content, "voice", exc)
        return False

    try:
        image_path = MEDIA_ROOT / "images" / f"{story.id}.png"
        generate_card(content.headline, story.source_name, image_path)
        content.image_path = str(image_path)
        content.status = "visual_ready"
        content.error_message = None
        db.commit()
    except Exception as exc:
        mark_content_failed(db, content, "visual", exc)
        return False

    try:
        captions_path = MEDIA_ROOT / "captions" / f"{story.id}.srt"
        build_captions(content.script_text, content.audio_duration_seconds or 0.0, captions_path)

        video_path = MEDIA_ROOT / "videos" / f"{story.id}.mp4"
        compose_video(
            image_path=Path(content.image_path),
            audio_path=Path(content.audio_path),
            captions_path=captions_path,
            output_path=video_path,
        )

        content.captions_path = str(captions_path)
        content.video_path = str(video_path)
        content.status = "video_ready"
        content.error_message = None
        db.commit()
    except Exception as exc:
        mark_content_failed(db, content, "video", exc)
        return False

    return True


@celery_app.task
def produce_episode_video(episode_id: int) -> dict:
    """
    Produce (or reuse) content for every primary story in an episode,
    in rank order, then concatenate the resulting per-story videos
    into one combined episode video.

    Idempotent: a story whose content is already video_ready is
    reused as-is, not regenerated. Fault-isolated: a story whose
    pipeline fails is skipped from the final video rather than
    blocking the rest of the episode.
    """

    with SessionLocal() as db:
        episode = db.get(Episode, episode_id)

        if episode is None:
            return {"episode_id": episode_id, "status": "failed", "error": "Episode not found"}

        episode.video_status = "producing"
        db.commit()

        rows = (
            db.query(EpisodeStory, Story)
            .join(Story, EpisodeStory.story_id == Story.id)
            .filter(
                EpisodeStory.episode_id == episode_id,
                EpisodeStory.selection_status == "primary",
            )
            .order_by(EpisodeStory.rank_position.asc())
            .all()
        )

        if not rows:
            episode.video_status = "failed"
            db.commit()
            return {"episode_id": episode_id, "status": "failed", "error": "No primary stories"}

        succeeded = 0
        skipped_existing = 0
        failed = 0
        video_paths: list[Path] = []

        for episode_story, story in rows:
            content = get_or_create_content(db, story.id)

            if content.status == "video_ready" and content.video_path:
                skipped_existing += 1
                video_paths.append(Path(content.video_path))
                continue

            ok = _produce_story_content(db, story, content)

            if ok:
                succeeded += 1
                video_paths.append(Path(content.video_path))
            else:
                failed += 1
                print(f"[episode_video] Story {story.id} failed, excluded from episode {episode_id}")

        if not video_paths:
            episode.video_status = "failed"
            db.commit()
            return {
                "episode_id": episode_id,
                "status": "failed",
                "error": "No stories produced successfully",
                "failed": failed,
            }

        output_path = MEDIA_ROOT / "videos" / f"episode_{episode_id}.mp4"

        try:
            concat_videos(video_paths, output_path)
            episode.video_path = str(output_path)
            episode.video_status = "ready"
            db.commit()
        except Exception as exc:
            episode.video_status = "failed"
            db.commit()
            print(f"[episode_video] Concat failed for episode {episode_id}: {exc}")
            return {"episode_id": episode_id, "status": "failed", "error": f"concat failed: {exc}"}

    result = {
        "episode_id": episode_id,
        "status": "ready",
        "stories_total": len(rows),
        "stories_produced": succeeded,
        "stories_reused": skipped_existing,
        "stories_failed": failed,
        "video_path": str(output_path),
    }

    print(f"[episode_video] Completed: {result}")

    return result
