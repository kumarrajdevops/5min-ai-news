from app.verification.engine import PRIMARY_SOURCE_CREDIBILITY_THRESHOLD, verify_story


def test_cross_source_confirmed_story_is_verified():
    status, reason = verify_story(
        source_name="Some Blog",
        credibility_score=0.60,
        duplicate_count=2,
    )
    assert status == "verified"
    assert "2 other outlet" in reason


def test_single_duplicate_is_enough_to_verify():
    status, _ = verify_story("Some Blog", credibility_score=0.60, duplicate_count=1)
    assert status == "verified"


def test_primary_source_self_verifies_without_corroboration():
    """
    An official company blog announcing its own product (e.g. OpenAI's
    own blog) shouldn't need a second outlet to "confirm" it -- it IS
    the primary source for its own news.
    """
    status, reason = verify_story(
        source_name="OpenAI",
        credibility_score=0.95,
        duplicate_count=0,
    )
    assert status == "verified"
    assert "Primary/official source" in reason
    assert "OpenAI" in reason


def test_exactly_at_threshold_counts_as_primary_source():
    status, _ = verify_story(
        "Borderline Source",
        credibility_score=PRIMARY_SOURCE_CREDIBILITY_THRESHOLD,
        duplicate_count=0,
    )
    assert status == "verified"


def test_low_credibility_single_source_is_unverified():
    status, reason = verify_story(
        source_name="Some Small Blog",
        credibility_score=0.60,
        duplicate_count=0,
    )
    assert status == "unverified"
    assert "Single source" in reason
    assert "no cross-source confirmation" in reason


def test_unverified_is_not_a_hard_exclusion_status():
    """
    Soft signal only -- "unverified" is a real, expected return value,
    not an exception or a sentinel meaning "reject this story". This
    test exists to make the intent explicit and catch any future
    change that turns this into a gate by accident.
    """
    status, _ = verify_story("Some Small Blog", credibility_score=0.10, duplicate_count=0)
    assert status in ("verified", "unverified")
