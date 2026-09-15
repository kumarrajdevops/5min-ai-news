# One-time script to re-resolve the real publisher for existing
# Hacker News stories (source_name previously always stored as
# "Hacker News", conflating discovery channel with actual publisher).


from app.db import SessionLocal
from app.models import Story
from app.sources.publisher_resolver import resolve_publisher


def backfill_hn_publisher() -> None:
    # Open a database session.
    with SessionLocal() as db:

        # Only Hacker News-discovered stories need re-resolving.
        stories = db.query(Story).filter(Story.source_type == "hackernews").all()

        # Show how many stories will be processed.
        print(f"Hacker News stories found: {len(stories)}")

        # Process every existing Hacker News story.
        for story in stories:

            old_source_name = story.source_name

            # Resolve the real publisher from the story's URL.
            story.source_name = resolve_publisher(story.url)

            # Display the change (or lack of one, for self-posts).
            print(
                f"[{story.id}] "
                f"{old_source_name!r} -> {story.source_name!r} | "
                f"title={story.title}"
            )

        # Persist all resolved publisher names.
        db.commit()

        # Confirm completion.
        print("Hacker News publisher backfill completed.")


if __name__ == "__main__":
    # Execute the backfill when this module is run directly.
    backfill_hn_publisher()
