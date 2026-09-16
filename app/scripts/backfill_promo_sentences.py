# One-time script: some already-generated StoryContent rows have a
# newsletter/subscription-pitch sentence baked into their summary/
# script_text (e.g. "To get stories like this in your inbox first,
# sign up here.") -- generated before app/content/script_generator.py's
# build_summary() started filtering those sentences out
# (PROMO_SENTENCE_RE). This re-runs generate_script() against each
# affected story's already-stored raw_summary (unchanged -- the fix is
# in filtering, not in the source text) so the promo sentence gets
# dropped this time.
#
# Only touches a story if its CURRENT summary still contains one of
# the promo trigger words -- the new code never produces that, so its
# presence is itself proof the content predates this fix and hasn't
# been hand-edited since (an editor's edit landing on the exact same
# phrase is not a realistic concern).

from app.content.script_generator import PROMO_SENTENCE_RE, generate_script
from app.db import SessionLocal
from app.models import Story, StoryContent


def backfill_promo_sentences() -> None:
    with SessionLocal() as db:
        rows = (
            db.query(StoryContent, Story)
            .join(Story, StoryContent.story_id == Story.id)
            .filter(StoryContent.summary.isnot(None))
            .all()
        )

        affected = [
            (content, story) for content, story in rows
            if PROMO_SENTENCE_RE.search(content.summary)
        ]

        print(f"StoryContent rows with a promo sentence baked in: {len(affected)}")

        for content, story in affected:
            script = generate_script(title=story.title, raw_summary=story.raw_summary)
            content.headline = script["headline"]
            content.summary = script["summary"]
            content.script_text = script["script_text"]
            content.status = "script_ready"
            content.audio_path = None
            content.audio_duration_seconds = None
            content.image_path = None
            content.captions_path = None
            content.video_path = None
            content.error_message = None
            print(f"[{story.id}] regenerated | title={story.title}")
            print(f"    -> {script['summary']}")

        db.commit()
        print(f"Done. {len(affected)} StoryContent row(s) regenerated.")


if __name__ == "__main__":
    backfill_promo_sentences()
