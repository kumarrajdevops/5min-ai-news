# One-time script: Hacker News link-posts had no real article content
# available from HN's own API, so their raw_summary was just "{points}
# points, {N} comments on Hacker News." -- see
# app/tasks/ingestion_hackernews.py's _build_summary(), now fixed to
# fetch the actual article page for future ingestions. This backfills
# already-stored stories: re-fetches each affected story's article page
# and, if that succeeds, updates the Story's raw_summary. Also
# regenerates that story's StoryContent (summary/script_text, resetting
# downstream audio/visual/video so a future Produce narrates the real
# summary) -- but ONLY when its current summary is still exactly the
# old junk text, i.e. never manually edited by an editor. A story
# already edited via the dashboard is left untouched.

import re

from app.content.script_generator import generate_script
from app.db import SessionLocal
from app.models import Story, StoryContent
from app.sources.article_fetcher import fetch_article_summary


JUNK_SUMMARY_RE = re.compile(r"^\d+ points, \d+ comments on Hacker News\.$")


def backfill_hn_summaries() -> None:
    with SessionLocal() as db:
        stories = db.query(Story).filter(Story.source_type == "hackernews").all()

        junk_stories = [
            s for s in stories
            if s.raw_summary and JUNK_SUMMARY_RE.match(s.raw_summary.strip())
        ]

        print(f"Hacker News link-posts with a junk summary: {len(junk_stories)}")

        fetch_failed = 0
        raw_summary_fixed = 0
        content_regenerated = 0
        content_skipped_edited = 0

        for story in junk_stories:
            fetched = fetch_article_summary(story.url)

            if not fetched:
                fetch_failed += 1
                print(f"[{story.id}] fetch failed/empty, left as-is | {story.title}")
                continue

            story.raw_summary = fetched
            raw_summary_fixed += 1
            print(f"[{story.id}] raw_summary updated | title={story.title}")
            print(f"    -> {fetched}")

            content = (
                db.query(StoryContent)
                .filter(StoryContent.story_id == story.id)
                .first()
            )

            if content is None:
                continue

            if content.summary and JUNK_SUMMARY_RE.match(content.summary.strip()):
                script = generate_script(title=story.title, raw_summary=fetched)
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
                content_regenerated += 1
                print("    -> story_content regenerated from the real summary")
            else:
                content_skipped_edited += 1
                print("    -> story_content left as-is (already edited/customized)")

        db.commit()

        print(
            f"Done. raw_summary fixed: {raw_summary_fixed}, "
            f"fetch failed: {fetch_failed}, "
            f"content regenerated: {content_regenerated}, "
            f"content skipped (already edited): {content_skipped_edited}"
        )


if __name__ == "__main__":
    backfill_hn_summaries()
