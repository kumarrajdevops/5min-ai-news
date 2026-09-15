# One-time script to recalculate AI relevance for existing stories.


from app.db import SessionLocal
from app.models import Story
from app.filters.ai_relevance import calculate_ai_relevance


def backfill_ai_relevance() -> None:
    # Open a database session.
    with SessionLocal() as db:

        # Load all existing stories so the new filter logic
        # can recalculate their classifications.
        stories = db.query(Story).all()

        # Show how many stories will be processed.
        print(f"Stories found: {len(stories)}")

        # Process every existing story.
        for story in stories:

            # Run the current AI relevance filter.
            ai_relevance, ai_score, filter_reason = (
                calculate_ai_relevance(
                    title=story.title,
                    summary=story.raw_summary,
                )
            )

            # Update the existing database row.
            story.ai_relevance = ai_relevance

            # Store the recalculated score.
            story.ai_relevance_score = ai_score

            # Store the recalculated explanation.
            story.filter_reason = filter_reason

            # Display the new classification.
            print(
                f"[{story.id}] "
                f"{story.ai_relevance} | "
                f"score={story.ai_relevance_score} | "
                f"{story.filter_reason} | "
                f"title={story.title}"
            )

        # Persist all recalculated classifications.
        db.commit()

        # Confirm completion.
        print("AI relevance backfill completed.")


if __name__ == "__main__":
    # Execute the backfill when this module is run directly.
    backfill_ai_relevance()
