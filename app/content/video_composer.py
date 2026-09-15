import re
import subprocess
from pathlib import Path


def get_audio_duration_seconds(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _format_srt_timestamp(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_captions(script_text: str, duration_seconds: float, output_path: Path) -> None:
    """
    Write an .srt caption file for `script_text`, timed against
    `duration_seconds`.

    This is a naive, proportional estimate: sentences are allocated a
    slice of the total audio duration proportional to their character
    count. It is NOT real forced alignment against the TTS engine's
    actual word timings -- good enough to burn in readable captions
    for this MVP, not frame-accurate. Real alignment is future work.
    """

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script_text) if s.strip()]
    if not sentences:
        sentences = [script_text]

    total_chars = sum(len(s) for s in sentences) or 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cursor = 0.0
    with open(output_path, "w", encoding="utf-8") as f:
        for index, sentence in enumerate(sentences, start=1):
            share = len(sentence) / total_chars
            segment_duration = duration_seconds * share
            start = cursor
            end = min(duration_seconds, cursor + segment_duration)
            cursor = end

            f.write(f"{index}\n")
            f.write(f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}\n")
            f.write(f"{sentence}\n\n")


def compose_video(
    image_path: Path,
    audio_path: Path,
    captions_path: Path,
    output_path: Path,
) -> None:
    """
    Compose a static-image + narration-audio + burned-in-captions
    video via ffmpeg. The image loops for the audio's duration
    (`-shortest` stops the output once the audio ends).
    """

    output_path.parent.mkdir(parents=True, exist_ok=True)

    subtitles_filter = (
        f"subtitles={captions_path}:force_style="
        f"'FontName=DejaVu Sans,FontSize=20,PrimaryColour=&HFFFFFF&'"
    )

    subprocess.run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-i", str(audio_path),
            "-vf", subtitles_filter,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
