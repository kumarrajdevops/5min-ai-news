from datetime import datetime, timedelta, timezone

import pytest

from app.ranking.engine import (
    VERIFICATION_BONUS,
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


def test_total_score_is_bounded_between_zero_and_one_when_not_verified():
    score, _ = compute_total_score(
        published_at=NOW,
        source_name="OpenAI",
        ai_relevance_score=1.0,
        duplicate_count=999,
        now=NOW,
        window_hours=WINDOW_HOURS,
    )
    assert 0.0 <= score <= 1.0


def test_verification_status_defaults_to_no_bonus():
    """
    compute_total_score must stay safe to call before every story has
    been through the Verification Engine -- omitting verification_status
    (the pre-existing call shape, still used wherever it isn't
    explicitly passed) must score identically to passing "pending".
    """
    score_omitted, _ = compute_total_score(
        published_at=NOW, source_name="OpenAI", ai_relevance_score=0.8,
        duplicate_count=0, now=NOW, window_hours=WINDOW_HOURS,
    )
    score_pending, _ = compute_total_score(
        published_at=NOW, source_name="OpenAI", ai_relevance_score=0.8,
        duplicate_count=0, now=NOW, window_hours=WINDOW_HOURS,
        verification_status="pending",
    )
    assert score_omitted == score_pending


def test_verified_story_scores_higher_than_otherwise_identical_unverified_story():
    verified_score, verified_reason = compute_total_score(
        published_at=NOW, source_name="Some Blog", ai_relevance_score=0.8,
        duplicate_count=0, now=NOW, window_hours=WINDOW_HOURS,
        verification_status="verified",
    )
    unverified_score, _ = compute_total_score(
        published_at=NOW, source_name="Some Blog", ai_relevance_score=0.8,
        duplicate_count=0, now=NOW, window_hours=WINDOW_HOURS,
        verification_status="unverified",
    )
    assert verified_score > unverified_score
    assert verified_score - unverified_score == pytest.approx(VERIFICATION_BONUS)
    assert "verification=verified" in verified_reason


def test_verification_bonus_is_a_small_flat_nudge_not_a_new_weighted_pillar():
    """
    The bonus is deliberately NOT folded into SCORE_WEIGHTS (which
    already sum to 1.0) -- at the extreme (every other factor maxed AND
    verified), total can exceed 1.0 by exactly VERIFICATION_BONUS, not a
    false claim that it's still hard-bounded to 1.0. Documented here so
    a future change to SCORE_WEIGHTS doesn't silently assume otherwise.
    Compares against the unverified case rather than asserting an exact
    absolute value, so this doesn't silently depend on OpenAI's specific
    credibility weight.
    """
    kwargs = dict(
        published_at=NOW, source_name="OpenAI", ai_relevance_score=1.0,
        duplicate_count=999, now=NOW, window_hours=WINDOW_HOURS,
    )
    score_unverified, _ = compute_total_score(**kwargs, verification_status="unverified")
    score_verified, _ = compute_total_score(**kwargs, verification_status="verified")

    assert score_verified - score_unverified == pytest.approx(VERIFICATION_BONUS)
    assert score_unverified <= 1.0  # every other factor maxes at exactly 1.0 combined
    assert score_verified > 1.0  # the bonus is what pushes it over
