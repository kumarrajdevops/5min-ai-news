from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.models import Story


def _insert_story(db, url, title="Some story"):
    story = Story(
        title=title,
        url=url,
        source_name="Example Source",
        source_type="rss",
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        status="collected",
        ai_relevance="ai_candidate",
    )
    db.add(story)
    db.commit()
    return story


def test_duplicate_url_raises_integrity_error_not_silent_corruption(db_session):
    """
    Sanity check that the underlying constraint this fix relies on
    actually fires under the test database too (SQLite, like Postgres,
    raises IntegrityError on a uq_stories_url violation via SQLAlchemy's
    backend-agnostic exception).
    """
    _insert_story(db_session, url="https://example.com/story")

    duplicate = Story(
        title="Different title, same url",
        url="https://example.com/story",
        source_name="Another Source",
        source_type="hackernews",
        published_at=datetime.now(timezone.utc),
        collected_at=datetime.now(timezone.utc),
        status="collected",
        ai_relevance="ai_candidate",
    )
    db_session.add(duplicate)

    try:
        db_session.commit()
        assert False, "expected an IntegrityError on the duplicate URL"
    except IntegrityError:
        db_session.rollback()


def test_per_row_commit_pattern_isolates_a_collision_from_other_inserts(db_session):
    """
    Direct regression for this session's ingestion race-condition fix
    (app/tasks/ingestion.py, app/tasks/ingestion_hackernews.py): a
    uq_stories_url collision on one entry must not roll back other
    valid inserts already committed in the same run -- reproduces the
    exact per-row commit + narrow except IntegrityError pattern those
    tasks now use, rather than the old single commit-at-the-end-of-
    the-batch approach that would have lost everything.
    """
    # A story that already exists (simulating another run having just
    # inserted it moments before this one's existing_story check ran).
    _insert_story(db_session, url="https://example.com/already-inserted")

    incoming_urls = [
        "https://example.com/new-story-1",
        "https://example.com/already-inserted",  # collides
        "https://example.com/new-story-2",
    ]

    inserted = 0
    duplicates = 0

    for url in incoming_urls:
        story = Story(
            title=f"Story for {url}",
            url=url,
            source_name="Example Source",
            source_type="rss",
            published_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc),
            status="collected",
            ai_relevance="ai_candidate",
        )
        db_session.add(story)

        try:
            db_session.commit()
            inserted += 1
        except IntegrityError:
            db_session.rollback()
            duplicates += 1

    assert inserted == 2
    assert duplicates == 1

    all_urls = {s.url for s in db_session.query(Story).all()}
    assert all_urls == {
        "https://example.com/already-inserted",
        "https://example.com/new-story-1",
        "https://example.com/new-story-2",
    }
