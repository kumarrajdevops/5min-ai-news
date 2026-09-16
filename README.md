# AI News Platform

Local-first pipeline for a daily Top-25 (+5 backup) AI technology news
video: ingest → deduplicate → rank/select → script/voice/visual/video
generation → Automated QA → human review (Editorial Dashboard) →
(publishing to YouTube/Instagram is a future phase).

> **Naming note:** the repo/dev project name (used by Docker Compose,
> container prefixes, etc.) is `5min-ai-news`. "AI News Platform" is
> the production/public brand name for the same project.

## Current slice

- FastAPI API
- PostgreSQL (schema managed by Alembic -- see "First-time setup" below)
- Redis + Celery worker
- Multi-source RSS ingestion (10 sources incl. OpenAI, Google AI,
  Google DeepMind, TechCrunch, The Verge, MIT Technology Review,
  NVIDIA, Hugging Face, Ars Technica, Wired) with a deterministic
  AI-relevance filter
- Hacker News ingestion (official Algolia search API) -- resolves the
  real publisher for link-posts (e.g. "The Guardian") instead of
  attributing everything to "Hacker News", so credibility scoring
  reflects the actual outlet
- Deterministic duplicate-story detection (title similarity + time window)
- Multi-factor ranking engine (recency, source credibility, AI
  relevance, cross-source momentum) + Top-25/5-backup selection,
  persisted per run as an "Episode"
- Script/voice/visual/video content generation, free/local (no API
  keys) -- runs per-story or across a full episode, produces one
  combined branded video with intro/outro
- Automated Video QA against the architecture's checklist (story
  count, AI-only, source links, captions/audio present, video
  integrity, duration target)
- Editorial Dashboard -- a browser UI for episode review: watch the
  video, reorder/swap Top 30 stories, edit scripts, run QA, approve/reject

## First-time setup

```bash
cp .env.example .env
docker compose up --build -d
docker compose exec api alembic upgrade head
```

The `alembic upgrade head` step is **required** before the API can
serve any data-backed endpoint -- the app does not auto-create
tables on startup (see `app/main.py`'s `startup()` docstring for why).

## Health check

```bash
curl http://localhost:8000/health
```

OpenAPI docs: http://localhost:8000/docs

## Running the pipeline

**1. Ingest news** (pulls from all enabled RSS sources, filters for
AI relevance, then automatically chains into deduplication):

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/rss
```

**2. (Optional) Also ingest Hacker News** (AI-related stories above a
points threshold, official Algolia API, chains into the same
deduplication step):

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/hackernews
```

**3. (Optional) Re-run deduplication manually**, without a full
ingestion cycle:

```bash
curl -X POST http://localhost:8000/api/v1/dedup/run
```

**4. Rank + select the Top 25 + 5 backups.** This is intentionally
a separate, manually-triggered step (not auto-chained after
ingestion) -- it's meant to run once, after the daily collection
window closes, not after every ingestion pass:

```bash
curl -X POST http://localhost:8000/api/v1/episodes/select
```

## Producing content (script + voice + visual + video)

**Single story.** Pick a `story_id` (e.g. from `/api/v1/episodes/latest`)
and kick off the full chain -- script generation, then voice synthesis,
then the visual card, then video composition, each auto-chained into
the next:

```bash
curl -X POST http://localhost:8000/api/v1/stories/{story_id}/produce
```

Poll for progress/results (`status` moves through `pending` ->
`script_ready` -> `voice_ready` -> `visual_ready` -> `video_ready`,
or `failed` -- see `error_message`):

```bash
curl http://localhost:8000/api/v1/stories/{story_id}/content
```

**Full episode.** Produce (or reuse) content for every primary story
in an episode and concatenate the results into one combined video, in
rank order:

```bash
curl -X POST http://localhost:8000/api/v1/episodes/{episode_id}/produce
```

Idempotent -- stories that already have `video_ready` content are
reused, not regenerated, so re-running after adding a few new stories
only produces what's missing. Fault-isolated -- a story whose pipeline
fails is skipped from the final video rather than blocking the whole
episode. `video_status` flips to `"producing"` synchronously, before
the endpoint even returns (closes a race where a poll landing before
the background task starts could mistake "not started yet" for
"already finished"). Poll `GET /api/v1/episodes/{episode_id}` for
`video_status` (`pending` -> `producing` -> `ready`, or `failed`),
`video_url`, and `video_produced_at`.

After the primary video is ready, the 5 backup stories are also
produced (or reused), best-effort, as a second phase that can never
delay or block the primary episode -- so a later dashboard swap
(promoting a backup to primary) is instant instead of triggering a
slow on-demand regeneration.

Both endpoints' responses include playable URLs (served from `/media`,
e.g. `http://localhost:8000/media/videos/{story_id}.mp4` or
`.../videos/episode_{episode_id}.mp4`) for the generated audio, image,
captions, and video. The combined episode video opens with a narrated
intro card ("AI Daily 25 -- [date] -- Today's Top 25 AI Stories") and
closes with a narrated outro ("That's all for today's AI Daily 25.
See you tomorrow.") -- still a straight concatenation otherwise, no
transitions or background music.

**Automated Video QA.** Once an episode is produced, validate it
against the architecture's QA checklist (story count, AI-only, source
links, captions/audio present, video integrity, duration target):

```bash
curl -X POST http://localhost:8000/api/v1/episodes/{episode_id}/qa
```

Poll `GET /api/v1/episodes/{episode_id}` for `qa_status`
(`pending` -> `passed`/`failed`), `qa_report` (per-check pass/fail
detail), and `qa_run_at`. `source_verification` always reports as not
implemented -- there's no Verification Engine yet -- rather than
faking a pass.

A QA result is stale once the episode is reproduced afterward
(`video_produced_at > qa_run_at`) -- the dashboard surfaces this as a
warning on its Run QA button rather than the API enforcing it.

All four stages are free/local, no API keys required:

- **Script** -- deterministic, template-based: headline + a
  deterministic summary of the story, nothing more (no editorializing
  or speculative "why it matters" commentary). Same pattern as the
  AI-relevance/dedup filters. For Hacker News link-posts (HN's API has
  no article content, only submission metadata), the summary is
  fetched from the linked article's own `og:description`/`meta
  description`/first paragraph (`app/sources/article_fetcher.py`)
  rather than falling back to "N points, M comments on Hacker News."
  Promotional/newsletter-pitch sentences ("subscribe", "sign up",
  etc.) are filtered out of any summary before narration.
- **Voice** -- [edge-tts](https://github.com/rany2/edge-tts) (free
  Microsoft neural TTS, one branded voice for every story).
- **Visual** -- a branded title card rendered with Pillow.
- **Video** -- ffmpeg composes the image + audio + burned-in captions
  into an mp4, hard-capped to the real audio duration (`-t
  <duration>`, not just `-shortest` -- see `TODO.md` for why that
  matters). A silent 0.5s clip is inserted between consecutive stories
  in the combined episode video for pacing. Captions are timed with a
  naive proportional estimate (not real forced alignment) -- see
  `TODO.md`.

## Editorial Dashboard

A browser UI for the human-in-the-loop review step -- browse episodes,
watch the produced video, review/reorder/edit the Top 30, check QA,
and approve or reject:

```text
http://localhost:8000/dashboard/
```

v1 is deliberately lightweight: vanilla HTML/CSS/JS
(`app/dashboard/`) served directly by FastAPI, no build step, no new
dependencies. Partially click-tested in a real browser via
`claude-in-chrome`; several real bugs (a Produce status race, stale
cached video playback, an edit-clobbering bug -- see `TODO.md`) were
only caught through actual live use once that browser connection
dropped mid-session, not through automated verification alone.

**What you can do from it:**

- **Browse episodes** -- list view links into each episode's Studio view.
- **Watch the video** -- native player; click a story's rank number to
  jump playback to roughly that point (computed from intro + preceding
  stories' narration durations).
- **Reorder the Top 30** -- drag a story within Primary or Backup to
  re-rank it (native HTML5 drag-and-drop, no library).
- **Swap in a backup** -- drag a Backup story onto a Primary slot to
  replace it (the "defective story" swap from the architecture's
  Top-30 Safety Mechanism). Since backups are pre-produced (see
  above), the swap is instant, no regeneration wait.
- **Edit a script** -- click a story's title to open headline/summary/
  script text as editable fields, alongside the source article link
  (opens in a new tab, plus a one-click Copy button) and its metadata
  (source, author, published/collected timestamps, and -- when the
  story was surfaced via an aggregator like Hacker News rather than
  ingested directly -- a "Discovered via" link back to that discussion
  thread). Saving invalidates that story's audio/visual/video so the
  next Produce regenerates them **from the edited script** (Produce
  no longer silently regenerates and overwrites a saved edit -- see
  `TODO.md`).
- **Proofread against the source** -- every story in the Top 30 list
  also shows its source article link (new tab + Copy button) directly
  below the title, not just in the edit panel.
- **Produce / Run QA** -- both buttons disable and show a live
  elapsed-time progress indicator while running, then auto-refresh
  the view when done (Produce polls `video_status`, QA polls
  `qa_run_at` against click time). Run QA shows an amber "stale"
  warning whenever the episode's been reproduced since QA last ran.
- **Approve / Reject** -- sets the episode's overall status. Doesn't
  hard-block on a failing QA result -- QA is surfaced prominently, but
  the human makes the final call.
- **Episode JSON (audit)** -- the exact API response the page rendered
  from, at the bottom of the Studio view: view, copy, or download it
  (`episode_{id}.json`) for a paper trail independent of the UI.

**The same actions as raw API calls** (for scripting, or anything the
UI doesn't cover):

```bash
# List every episode
curl http://localhost:8000/api/v1/episodes

# Edit a story's script (only provided fields change)
curl -X PATCH http://localhost:8000/api/v1/stories/{story_id}/content \
  -H "Content-Type: application/json" \
  -d '{"script_text": "..."}'

# Reorder one group's (primary or backup) full rank order
curl -X POST http://localhost:8000/api/v1/episodes/{episode_id}/reorder \
  -H "Content-Type: application/json" \
  -d '{"story_ids": [15, 16, 22, ...]}'

# Swap a backup into a primary slot
curl -X POST http://localhost:8000/api/v1/episodes/{episode_id}/swap \
  -H "Content-Type: application/json" \
  -d '{"primary_story_id": 39, "backup_story_id": 21}'

# Approve / reject
curl -X POST http://localhost:8000/api/v1/episodes/{episode_id}/approve
curl -X POST http://localhost:8000/api/v1/episodes/{episode_id}/reject
```

YouTube/Instagram publishing, analytics, and the fuller Next.js-based
vision from `dashboard-proposal.md` are a separate, later workstream
-- see `TODO.md`.

## Inspecting results

```bash
# All AI-candidate stories, deduplicated (canonical only)
curl http://localhost:8000/api/v1/stories

# Every story grouped as a duplicate of a given canonical story
curl http://localhost:8000/api/v1/stories/{story_id}/duplicates

# Every episode, newest first (id, status, video/QA status, counts)
curl http://localhost:8000/api/v1/episodes

# The most recently selected episode (Top 25 + backups, with scores
# and per-story ranking rationale)
curl http://localhost:8000/api/v1/episodes/latest

# A specific episode by id
curl http://localhost:8000/api/v1/episodes/{episode_id}
```

## Stop / reset

```bash
docker compose down       # stop, keep data
docker compose down -v    # stop and wipe the database volume
```

## Contributing / guardrails

`CLAUDE.md` documents dev-environment gotchas and hard rules distilled
from real bugs found in this project (script-clobbering, stale cached
media, background-task status races, ffmpeg duration overrun, and
more) -- read it before touching the content/video pipeline or
dashboard. `.claude/skills/verify-episode/` and
`.claude/agents/episode-verifier.md` codify the AV-sync/QA/idempotency
checklist used to catch and verify those bugs, for reuse on future
pipeline changes.