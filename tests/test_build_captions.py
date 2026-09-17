from app.content.video_composer import build_captions


def test_build_captions_writes_real_segment_timing(tmp_path):
    """
    Regression for the "captions drift on uneven sentences" known
    issue: build_captions() must use the real per-sentence start/end
    times edge-tts reports (see synthesize_voice()), not derive its
    own timing from character counts. A short sentence followed by a
    much longer one -- the exact case that broke the old proportional
    estimate -- must still land on its real, disproportionate share of
    the audio.
    """
    segments = [
        {"text": "Yes.", "start": 0.1, "end": 0.6},
        {"text": "This is a much longer sentence that takes far more time to speak aloud.", "start": 0.6, "end": 6.2},
    ]
    output_path = tmp_path / "captions.srt"

    build_captions(segments, output_path)

    srt = output_path.read_text(encoding="utf-8")
    assert "00:00:00,100 --> 00:00:00,600" in srt
    assert "Yes." in srt
    assert "00:00:00,600 --> 00:00:06,200" in srt
    assert "This is a much longer sentence" in srt


def test_build_captions_handles_no_segments(tmp_path):
    output_path = tmp_path / "captions.srt"
    build_captions([], output_path)
    assert output_path.read_text(encoding="utf-8") == ""
