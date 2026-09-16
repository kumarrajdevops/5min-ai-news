from datetime import datetime, timedelta, timezone

from app.ranking.engine import (
    compute_credibility_score,
    compute_momentum_score,
    compute_recency_score,
    compute_total_score,
)


NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
WINDOW_HOURS = 24.0


def test_recency_score_is_max_for_just_published():
    score = compute_recency_score(NOW, NOW, WINDOW_HOURS)
    assert score == 1.0


def test_recency_score_decays_linearly_to_zero_at_window_edge():
    published = NOW - timedelta(hours=WINDOW_HOURS)
    score = compute_recency_score(published, NOW, WINDOW_HOURS)
    assert score == 0.0


def test_recency_score_clamps_for_stories_older_than_window():
    published = NOW - timedelta(hours=WINDOW_HOURS * 3)
    score = compute_recency_score(published, NOW, WINDOW_HOURS)
    assert score == 0.0


def test_recency_score_is_between_zero_and_one_midway():
    published = NOW - timedelta(hours=WINDOW_HOURS / 2)
    score = compute_recency_score(published, NOW, WINDOW_HOURS)
    assert 0.0 < score < 1.0


def test_credibility_score_uses_curated_weight():
    assert compute_credibility_score("OpenAI") == 0.95


def test_credibility_score_falls_back_to_default_for_unknown_source():
    assert compute_credibility_score("Some Brand New Blog Nobody Curated") == 0.60


def test_momentum_score_zero_duplicates_is_zero():
    assert compute_momentum_score(0) == 0.0


def test_momentum_score_caps_at_one():
    assert compute_momentum_score(100, cap=3) == 1.0


def test_momentum_score_scales_toward_cap():
    assert compute_momentum_score(1, cap=3) == 1.0 / 3.0


def test_total_score_missing_published_at_treated_as_worst_recency_not_a_crash():
    score, reason = compute_total_score(
        published_at=None,
        source_name="OpenAI",
        ai_relevance_score=0.9,
        duplicate_count=0,
        now=NOW,
        window_hours=WINDOW_HOURS,
    )
    assert score >= 0.0
    assert isinstance(reason, str)


def test_fresh_relevant_story_beats_stale_high_momentum_story():
    """
    Direct regression for the sanity check already referenced in
    app/ranking/engine.py's own SCORE_WEIGHTS comment: a stale story
    with max momentum should still lose to a fresh, relevant one.
    """
    fresh_score, _ = compute_total_score(
        published_at=NOW,
        source_name="OpenAI",
        ai_relevance_score=1.0,
        duplicate_count=0,
        now=NOW,
        window_hours=WINDOW_HOURS,
    )

    stale_high_momentum_score, _ = compute_total_score(
        published_at=NOW - timedelta(hours=WINDOW_HOURS),
        source_name="OpenAI",
        ai_relevance_score=1.0,
        duplicate_count=10,
        now=NOW,
        window_hours=WINDOW_HOURS,
    )

    assert fresh_score > stale_high_momentum_score


def test_total_score_is_bounded_between_zero_and_one():
    score, _ = compute_total_score(
        published_at=NOW,
        source_name="OpenAI",
        ai_relevance_score=1.0,
        duplicate_count=999,
        now=NOW,
        window_hours=WINDOW_HOURS,
    )
    assert 0.0 <= score <= 1.0
