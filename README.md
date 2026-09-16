# AI News Platform

Local-first pipeline for a daily Top-25 (+5 backup) AI technology
news video: ingest → deduplicate → rank/select → (script/voice/video
generation and publishing are future phases).

> **Naming note:** the repo/dev project name (used by Docker Compose,
> container prefixes, etc.) is `5min-ai-news`. "AI News Platform" is
> the production/public brand name for the same project.

## Current slice

- FastAPI API
- PostgreSQL (schema managed by Alembic -- see "First-time setup" below)
- Redis + Celery worker
- Multi-source RSS ingestion with a deterministic AI-relevance filter
- Deterministic duplicate-story detection (title similarity + time window)
- Multi-factor ranking engine (recency, source credibility, AI
  relevance, cross-source momentum) + Top-25/5-backup selection,
  persisted per run as an "Episode"

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

**2. (Optional) Re-run deduplication manually**, without a full
ingestion cycle:

```bash
curl -X POST http://localhost:8000/api/v1/dedup/run
```

**3. Rank + select the Top 25 + 5 backups.** This is intentionally
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
episode. Poll `GET /api/v1/episodes/{episode_id}` for `video_status`
(`pending` -> `producing` -> `ready`, or `failed`) and `video_url`.

Both endpoints' responses include playable URLs (served from `/media`,
e.g. `http://localhost:8000/media/videos/{story_id}.mp4` or
`.../videos/episode_{episode_id}.mp4`) for the generated audio, image,
captions, and video. The combined episode video opens with a narrated
intro card ("AI Daily 25 -- [date] -- Today's Top 25 AI Stories") and
closes with a narrated outro ("That's all for today's AI Daily 25.
See you tomorrow.") -- still a straight concatenation otherwise, no
transitions or background music.

All four stages are free/local, no API keys required:

- **Script** -- deterministic, template-based: headline + a
  deterministic summary of the story, nothing more (no editorializing
  or speculative "why it matters" commentary). Same pattern as the
  AI-relevance/dedup filters.
- **Voice** -- [edge-tts](https://github.com/rany2/edge-tts) (free
  Microsoft neural TTS, one branded voice for every story).
- **Visual** -- a branded title card rendered with Pillow.
- **Video** -- ffmpeg composes the image + audio + burned-in captions
  into an mp4. Captions are timed with a naive proportional estimate
  (not real forced alignment) -- see `TODO.md`.

## Inspecting results

```bash
# All AI-candidate stories, deduplicated (canonical only)
curl http://localhost:8000/api/v1/stories

# Every story grouped as a duplicate of a given canonical story
curl http://localhost:8000/api/v1/stories/{story_id}/duplicates

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