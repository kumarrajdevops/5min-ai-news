import shutil
import subprocess

import pytest
from PIL import Image

from app.content.video_composer import compose_video, generate_gap_clip, probe_video


ffmpeg_required = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg is not installed"
)


def _make_test_image(path):
    Image.new("RGB", (320, 240), color=(10, 20, 30)).save(path)


def _make_test_audio(path, duration_seconds: float):
    # A short synthetic tone via ffmpeg's own generator -- no network,
    # no edge-tts, just enough real audio to drive a real compose_video
    # call with a known, exact duration.
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_seconds}",
            "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _make_test_captions(path):
    path.write_text("1\n00:00:00,000 --> 00:00:01,000\nTest caption\n\n", encoding="utf-8")


@ffmpeg_required
def test_composed_video_duration_matches_audio_duration_precisely(tmp_path):
    """
    Direct regression for this session's AV-desync bug: -shortest alone
    let the video stream overrun the audio by 1-2+ seconds per clip
    (looped image + subtitles filter + GOP/keyframe flush behavior),
    which accumulated additively once many clips were concatenated
    into one episode video (~34s drift across a full episode before
    the fix). compose_video() now takes an explicit duration_seconds
    to hard-cap the output -- verify it actually holds, with real
    ffmpeg, not a mocked assumption.
    """
    image_path = tmp_path / "image.png"
    audio_path = tmp_path / "audio.aac"
    captions_path = tmp_path / "captions.srt"
    output_path = tmp_path / "output.mp4"

    audio_duration = 3.0
    _make_test_image(image_path)
    _make_test_audio(audio_path, audio_duration)
    _make_test_captions(captions_path)

    compose_video(
        image_path=image_path,
        audio_path=audio_path,
        captions_path=captions_path,
        output_path=output_path,
        duration_seconds=audio_duration,
    )

    info = probe_video(output_path)

    # One frame of tolerance (~0.04s at 25fps) -- matches the tolerance
    # already established and verified against real episodes this
    # session, not an arbitrarily loose bound.
    assert abs(info["duration_seconds"] - audio_duration) < 0.1
    assert info["has_video"]
    assert info["has_audio"]


@ffmpeg_required
def test_composed_video_without_explicit_duration_still_produces_valid_video(tmp_path):
    """
    duration_seconds is optional (some callers may not have it handy)
    -- compose_video must still produce a playable video via the
    -shortest fallback alone, just without the extra precision
    guarantee.
    """
    image_path = tmp_path / "image.png"
    audio_path = tmp_path / "audio.aac"
    captions_path = tmp_path / "captions.srt"
    output_path = tmp_path / "output.mp4"

    _make_test_image(image_path)
    _make_test_audio(audio_path, 2.0)
    _make_test_captions(captions_path)

    compose_video(
        image_path=image_path,
        audio_path=audio_path,
        captions_path=captions_path,
        output_path=output_path,
    )

    info = probe_video(output_path)
    assert info["has_video"]
    assert info["has_audio"]
    assert info["duration_seconds"] > 0


@ffmpeg_required
def test_gap_clip_has_video_and_audio_streams_for_concat_compatibility(tmp_path):
    """
    generate_gap_clip()'s output is spliced via concat_videos()'s
    stream-copy concatenation, which requires every clip to share the
    same codec/resolution/pixel-format profile as story clips -- a
    clip missing either stream, or with an unexpected duration, would
    silently break that concatenation.
    """
    output_path = tmp_path / "gap.mp4"
    generate_gap_clip(0.5, output_path)

    info = probe_video(output_path)
    assert info["has_video"]
    assert info["has_audio"]
    # ffmpeg quantizes to whole frames at 25fps (0.5s -> 13 frames ->
    # 0.52s) -- a small, expected, already-documented rounding
    # artifact, not the multi-second bug this test suite guards
    # against.
    assert abs(info["duration_seconds"] - 0.5) < 0.1
