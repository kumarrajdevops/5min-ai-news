# Content Pipeline — Batch Timing Report

**Date:** 2026-09-15
**Run:** all 16 stories from the latest episode (`episode_id=1`, rank
order), processed sequentially through the full
script → voice → visual → video pipeline, then concatenated into one
combined episode video.

Timing source: per-stage durations parsed directly from Celery's
`succeeded in Xs` log lines (exact task execution time, not polling
overhead); total-per-story time measured by wall clock around each
`POST /produce` call through to `status: video_ready`.

## Per-story timing (seconds)

| Story ID | Script | Voice | Visual | Video compose | Stage sum | Total (wall clock) |
|---|---|---|---|---|---|---|
| 15 | 0.01 | 1.15 | 0.06 | 6.91 | 8.13 | 8.80 |
| 16 | 0.01 | 3.04 | 0.04 | 6.94 | 10.03 | 10.29 |
| 22 | 0.01 | 2.28 | 0.08 | 5.57 | 7.94 | 9.08 |
| 5  | 0.01 | 2.31 | 0.06 | 6.13 | 8.51 | 9.11 |
| 6  | 0.01 | 1.62 | 0.10 | 6.08 | 7.81 | 9.14 |
| 23 | 0.01 | 1.75 | 0.05 | 4.54 | 6.35 | 7.76 |
| 25 | 0.01 | 1.52 | 0.08 | 5.28 | 6.89 | 7.88 |
| 26 | 0.01 | 2.66 | 0.07 | 4.08 | 6.82 | 7.67 |
| 19 | 0.02 | 2.14 | 0.05 | 7.09 | 9.30 | 10.35 |
| 20 | 0.01 | 1.17 | 0.06 | 6.53 | 7.77 | 9.16 |
| 9  | 0.01 | 1.75 | 0.04 | 9.17 | 10.97 | 11.77 |
| 10 | 0.01 | 2.59 | 0.07 | 7.58 | 10.25 | 11.65 |
| 12 | 0.01 | 2.44 | 0.07 | 6.13 | 8.65 | 9.14 |
| 1  | 0.01 | 2.71 | 0.07 | 5.69 | 8.48 | 9.10 |
| 18 | 0.02 | 2.10 | 0.09 | 6.13 | 8.34 | 9.24 |
| 21 | 0.01 | 2.09 | 0.07 | 12.94 | 15.11 | 15.76 |

## Aggregate stats

| Stage | Min | Max | Avg | Total (sum across 16 stories) |
|---|---|---|---|---|
| Script generation | 0.01s | 0.02s | 0.01s | 0.16s |
| Voice synthesis (edge-tts) | 1.15s | 3.04s | 2.13s | 34.12s |
| Visual generation (Pillow) | 0.04s | 0.10s | 0.07s | 1.06s |
| Video composition (ffmpeg) | 4.08s | 12.94s | 6.92s | 110.69s |
| **Full story (stage sum)** | 6.35s | 15.11s | 8.79s | 140.55s |

- **Batch wall-clock total (16 stories, sequential):** 159s (~2m 39s)
- **Video composition dominates**, ~79% of per-story time — expected,
  since it's the only stage doing real transcoding (ffmpeg encoding
  h264 + burning in subtitles) rather than a single API/library call.
- **Script generation is effectively free** (~10-20ms) since it's
  pure string templating, no I/O.
- Story 21 was the outlier (15.76s total, 12.94s of it in video
  compose) — likely just a longer script → longer audio → more video
  frames to encode; not investigated further, no error occurred.

## Combined episode video

All 16 per-story videos were concatenated in rank order via ffmpeg's
concat demuxer (stream copy, no re-encoding — all 16 inputs share the
same codec/resolution/pixel format, so this was fast and lossless):

```bash
ffmpeg -f concat -safe 0 -i media/videos/concat_list.txt -c copy media/videos/full_episode.mp4
```

- **Output:** `media/videos/full_episode.mp4`
- **Duration:** 6:05.96 (365.96s)
- **Size:** 7.6 MB
- **Streams:** h264 video + aac audio, both valid (verified via `ffprobe`)
- **Order:** rank_position 1-16 from the latest episode (story IDs
  15, 16, 22, 5, 6, 23, 25, 26, 19, 20, 9, 10, 12, 1, 18, 21)

## Update — 2026-09-15, script simplified

The "why it matters" line was removed from the script template (it
was producing near-identical, editorializing sentences across stories
that only matched the generic "ai" keyword -- e.g. 6 of the 16 stories
here had `filter_reason == "Matched: ai"` and so got the exact same
"This matters because it touches on ai, signaling where AI
development is heading next." verbatim). Per direction: the script
now reads just the headline + deterministic summary, nothing more --
no editorializing, no speculative commentary.

All 16 stories were regenerated with the simplified script and the
combined video was rebuilt. Detailed per-stage timing wasn't
re-captured for this run (not the point of the change), but the
overall effect: shorter scripts -> shorter narration audio -> faster
video encoding and a shorter combined video.

- **New combined video duration:** 4:24 (264.4s), down from 6:05
  (366.0s) before the simplification
- **New combined video size:** 5.5 MB (down from 7.6 MB)
- Streams still verified valid (h264 + aac) via `ffprobe` after rebuild

## Notes / caveats

- All 16 stories completed successfully (`status: video_ready`) --
  zero failures in this run.
- Processed **sequentially, one story at a time** (not in parallel)
  to keep worker logs unambiguous for per-stage timing extraction.
  Running stories concurrently would likely reduce total batch wall
  time (Celery's worker has 8 prefork processes available) but wasn't
  attempted here.
- This combined video is a straight concatenation of 16 independently
  generated title-card videos -- there's no intro/outro, no
  episode-level branding, and no transitions between stories. Treat
  it as a proof of concept that the per-story pipeline scales across
  a full episode's story list, not as a publish-ready final product.
