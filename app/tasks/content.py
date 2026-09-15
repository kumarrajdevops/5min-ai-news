from pathlib import Path

from app.content.script_generator import generate_script
from app.content.video_composer import build_captions, compose_video, get_audio_duration_seconds
from app.content.visual_generator import generate_card
from app.content.voice_generator import synthesize_voice
from app.db import SessionLocal
from app.models import Story, StoryContent
from app.worker.celery_app import celery_app


# Object-storage-style layout, matching the folder structure described
# in the architecture (raw-news/, images/, audio/, captions/, videos/).
# Local filesystem for now, under the project's bind-mounted volume;
# swapping this for S3 later only touches this constant + the path
# helpers, not the task logic.
MEDIA_ROOT = Path("media")


def _get_or_create_content(db, story_id: int) -> StoryContent:
    content = (
        db.query(StoryContent)
        .filter(StoryContent.story_id == story_id)
        .first()
    )

    if content is None:
        content = StoryContent(story_id=story_id, status="pending")
        db.add(content)
        db.flush()

    return content


def _mark_failed(db, content: StoryContent, stage: str, exc: Exception) -> None:
    content.status = "failed"
    content.error_message = f"[{stage}] {exc}"
    db.commit()
    print(f"[content] {stage} failed for story {content.story_id}: {exc}")


@celery_app.task
def generate_script_task(story_id: int) -> dict:
    """
    Stage 1 of 4: deterministic, template-based script generation.
    Chains into generate_voice_task on success.
    """

    with SessionLocal() as db:
        story = db.get(Story, story_id)

        if story is None:
            return {"story_id": story_id, "status": "failed", "error": "Story not found"}

        content = _get_or_create_content(db, story_id)

        try:
            script = generate_script(
                title=story.title,
                raw_summary=story.raw_summary,
                filter_reason=story.filter_reason,
                source_name=story.source_name,
            )

            content.headline = script["headline"]
            content.summary = script["summary"]
            content.why_it_matters = script["why_it_matters"]
            content.script_text = script["script_text"]
            content.status = "script_ready"
            content.error_message = None
            db.commit()

        except Exception as exc:
            _mark_failed(db, content, "script", exc)
            return {"story_id": story_id, "status": "failed", "stage": "script"}

    print(f"[content] Script generated for story {story_id}")
    generate_voice_task.delay(story_id)
    return {"story_id": story_id, "status": "script_ready"}


@celery_app.task
def generate_voice_task(story_id: int) -> dict:
    """
    Stage 2 of 4: synthesize narration audio from the generated script
    via edge-tts (free, no API key). Chains into generate_visual_task.
    """

    with SessionLocal() as db:
        content = (
            db.query(StoryContent)
            .filter(StoryContent.story_id == story_id)
            .first()
        )

        if content is None or not content.script_text:
            return {"story_id": story_id, "status": "failed", "error": "No script found"}

        try:
            audio_path = MEDIA_ROOT / "audio" / f"{story_id}.mp3"
            synthesize_voice(content.script_text, audio_path)
            duration = get_audio_duration_seconds(audio_path)

            content.audio_path = str(audio_path)
            content.audio_duration_seconds = duration
            content.status = "voice_ready"
            content.error_message = None
            db.commit()

        except Exception as exc:
            _mark_failed(db, content, "voice", exc)
            return {"story_id": story_id, "status": "failed", "stage": "voice"}

    print(f"[content] Voice generated for story {story_id}")
    generate_visual_task.delay(story_id)
    return {"story_id": story_id, "status": "voice_ready"}


@celery_app.task
def generate_visual_task(story_id: int) -> dict:
    """
    Stage 3 of 4: render a branded title card via Pillow (no API key).
    Chains into compose_video_task.
    """

    with SessionLocal() as db:
        content = (
            db.query(StoryContent)
            .filter(StoryContent.story_id == story_id)
            .first()
        )
        story = db.get(Story, story_id)

        if content is None or story is None:
            return {"story_id": story_id, "status": "failed", "error": "No content/story found"}

        try:
            image_path = MEDIA_ROOT / "images" / f"{story_id}.png"
            generate_card(content.headline, story.source_name, image_path)

            content.image_path = str(image_path)
            content.status = "visual_ready"
            content.error_message = None
            db.commit()

        except Exception as exc:
            _mark_failed(db, content, "visual", exc)
            return {"story_id": story_id, "status": "failed", "stage": "visual"}

    print(f"[content] Visual generated for story {story_id}")
    compose_video_task.delay(story_id)
    return {"story_id": story_id, "status": "visual_ready"}


@celery_app.task
def compose_video_task(story_id: int) -> dict:
    """
    Stage 4 of 4: burn proportional captions in and compose the final
    video (image + audio + captions) via ffmpeg. Terminal stage.
    """

    with SessionLocal() as db:
        content = (
            db.query(StoryContent)
            .filter(StoryContent.story_id == story_id)
            .first()
        )

        if content is None:
            return {"story_id": story_id, "status": "failed", "error": "No content found"}

        try:
            captions_path = MEDIA_ROOT / "captions" / f"{story_id}.srt"
            build_captions(
                content.script_text,
                content.audio_duration_seconds or 0.0,
                captions_path,
            )

            video_path = MEDIA_ROOT / "videos" / f"{story_id}.mp4"
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
            _mark_failed(db, content, "video", exc)
            return {"story_id": story_id, "status": "failed", "stage": "video"}

    print(f"[content] Video composed for story {story_id}")
    return {"story_id": story_id, "status": "video_ready"}
