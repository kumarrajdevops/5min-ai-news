# TODO — AI News Platform (5min-ai-news)

Tracks implementation progress against the architecture in
[`project.md`](project.md). Update this file as work completes or
new work is identified — check items off in place rather than
deleting history, so it stays a running log.

## Done

### Core pipeline (pre-existing, per README "Current slice")
- [x] FastAPI API scaffold
- [x] PostgreSQL schema managed via Alembic
- [x] Redis + Celery worker
- [x] Multi-source RSS ingestion with deterministic AI-relevance filter
- [x] Deterministic duplicate-story detection (title similarity + time window)
- [x] Multi-factor ranking engine (recency, source credibility, AI
      relevance, cross-source momentum) + Top-25/5-backup selection,
      persisted as an "Episode"

### This session — 2026-09-15
- [x] Read `project.md` (architecture baseline) and full repo, reviewed every app file
- [x] Stopped stale containers running under the old `5min-ai-news` prefix before rebuilding
- [x] Fixed `docker-compose.yml` project name mismatch (`ai-news-platform` → `5min-ai-news`)
      so Compose reuses the real Postgres volume instead of silently creating an empty one
- [x] Added naming note to `README.md`: `5min-ai-news` = repo/dev name,
      "AI News Platform" = production/public brand
- [x] Built and started the stack (`docker compose up --build -d`), verified all 4
      services (api, worker, postgres, redis) healthy
- [x] Found and documented critical bug: no baseline Alembic migration created the
      `stories` table — `alembic upgrade head` failed on a fresh DB, breaking every
      data endpoint (ingestion, dedup, ranking, `/api/v1/stories`)
- [x] Wrote up findings in `errors.md` (renamed from `errors.txt`)
- [x] Added `alembic/versions/6f1e2a7b9c04_create_stories_table.py` as the true
      baseline migration; re-pointed `996b16094585`'s `down_revision` to it
- [x] Verified `alembic upgrade head` succeeds cleanly on a fresh DB (4 tables created)
- [x] Re-tested full pipeline end-to-end: ingestion (26 stories inserted from 2153
      seen across 8 sources) → dedup (0 duplicates, expected on first run) →
      ranking/episode selection (16 stories ranked and scored correctly)
- [x] Removed orphaned, empty `ai-news-platform_postgres_data` Docker volume
- [x] Renamed `project.txt` → `project.md`, `errors.txt` → `errors.md`
- [x] Created this `TODO.md` to track ongoing work
- [x] Ran a stability pass: ~15 min of live use (repeated ingestion/dedup/ranking
      triggers), all 4 containers stayed healthy, ingestion confirmed idempotent
      on re-run, dedup stable, 404s and query-param clamping verified correct.
      See `errors.md` sections 4-5.
- [x] Fixed the `run_date` validation bug: `trigger_ranking_selection()` now
      validates with `date.fromisoformat()` and returns HTTP 422 with a clear
      message on bad input, instead of silently queuing a task that fails in
      the worker. Verified against the live API. See `errors.md` §4 update.

### This session — 2026-09-15, part 2 (script/voice/visual/video, one-story proof of concept)
- [x] Added `story_content` table (1:1 with `stories`) tracking generated
      script/audio/image/captions/video paths and a `status` progress field
- [x] Script generation: deterministic, template-based (`app/content/script_generator.py`)
      -- headline, summary (HTML-stripped RSS summary), "why it matters"
      (built from the AI-relevance filter's already-computed keywords).
      No LLM, no API key -- same pattern as the existing AI-relevance/dedup filters.
- [x] Voice generation: `edge-tts` (`app/content/voice_generator.py`), one hardcoded
      branded voice (`en-US-GuyNeural`), free, no API key
- [x] Visual generation: Pillow-rendered branded title card (`app/content/visual_generator.py`),
      no API key
- [x] Video composition: ffmpeg combines image + audio + burned-in captions into
      an mp4 (`app/content/video_composer.py`); captions timed via a naive
      proportional estimate (character-count share of total audio duration)
- [x] New Celery chain (`app/tasks/content.py`): `generate_script_task` ->
      `generate_voice_task` -> `generate_visual_task` -> `compose_video_task`,
      each stage persisting progress/failure to `story_content.status`
- [x] New endpoints: `POST /api/v1/stories/{id}/produce`,
      `GET /api/v1/stories/{id}/content`; `/media` mounted via `StaticFiles`
      so generated audio/image/video are directly playable by URL
- [x] Dockerfile: added `ffmpeg` + `fonts-dejavu-core` (apt packages)
- [x] requirements.txt: added `edge-tts` and `Pillow`
- [x] **Bug found and fixed during testing:** pinned `edge-tts==6.1.9` failed
      every synthesis call with `403 Invalid response status` -- Microsoft's
      TTS endpoint now requires a `Sec-MS-GEC` signed token that 6.1.9
      predates. Bumped to `edge-tts==7.2.8` (latest at the time), fixed.
- [x] Verified end-to-end on story #15 (the top-ranked story from the latest
      episode): real ~30s narrated audio, correctly rendered branded visual
      card (Unicode included), proportionally-timed captions, valid h264/aac
      mp4 (confirmed via `ffprobe`). Also ruled out a false alarm: `’`
      appeared as mojibake in one local test command's output, but the raw
      Postgres bytes were correct UTF-8 the whole time -- a Windows/Git-Bash
      terminal decoding artifact in the test tool, not an app bug.

### This session — 2026-09-15, part 3 (summary truncation bug)
- [x] **Bug found and fixed:** `build_summary()` was including the source
      RSS feed's own truncated-excerpt marker (e.g. "...signing on at least
      partially to a [&#8230;]") as if it were a complete sentence, producing
      scripts that read as dangling mid-thought. Added `TRUNCATION_MARKER_RE`
      to detect and drop a trailing truncated fragment before assembling the
      summary. Verified on story #15: summary now ends cleanly at the last
      complete sentence.
- [x] **Learned:** the `worker` container does not hot-reload on code changes
      like the `api` container's `uvicorn --reload` does -- Celery loads task
      modules once at process startup and keeps them in memory. After editing
      any `app/tasks/*` or `app/content/*` file, `docker compose restart
      worker` is required before re-running a task, or the old code silently
      keeps running.

### This session — 2026-09-15, part 4 (source list expansion)
- [x] Reviewed an external analysis (`public-response.md`) of the episode/video
      pipeline; verified its claims against the live system rather than
      accepting them at face value. Its "Top-25 selection: Not Achieved" framing
      was misleading -- confirmed there are only 16 total canonical
      AI-candidate stories in the whole database right now (not a broken
      selector; the code correctly doesn't pad to 25 with fewer than 30
      candidates, already verified in `errors.md`). "Episode 3" was also just
      an artifact of earlier manual re-testing, not 3 real daily runs.
- [x] Answered directly: with the 8 sources enabled at the time, one real
      ingestion pass produced 2153 RSS entries seen -> 26 inserted -> only 16
      AI-candidate canonical stories. Not close to 30/day, and nothing was
      actually "global" (all sources English-language, US-centric tech press).
- [x] Researched and verified (via live `curl`, not just search results) two
      new officially-hosted, active RSS sources and added them to
      `app/sources/registry.py` + `app/ranking/engine.py`'s `CREDIBILITY_WEIGHTS`:
      **Google DeepMind News** (`https://deepmind.google/blog/rss.xml`) and
      **Wired — Artificial Intelligence** (`https://www.wired.com/feed/tag/ai/latest/rss`).
- [x] **Researched and deliberately skipped** (documented so this isn't
      silently re-researched later):
      - Anthropic, Meta AI -- no official RSS feed exists at all, only
        unofficial third-party scraper mirrors (e.g. GitHub Pages projects
        re-scraping their blogs). Skipped per user decision: same fragility
        class already worked around with VentureBeat/Microsoft AI Blog.
      - CNBC Technology -- the feed ID found via search was actually a video
        show feed ("Squawk Box Europe"), not Technology news. Dropped rather
        than guess further; the real Technology feed URL wasn't confirmed.
      - Axios AI, Engadget's AI tag, Business Insider, TechRadar's AI
        category -- no confirmed direct feed URL found in this research pass.
        Candidates for a future pass, not confirmed dead ends.
- [ ] **Two new sources alone do not guarantee ~30/day.** This is incremental,
      not a fix -- reaching a reliable daily average needs either more
      verified-source research passes, or the not-yet-built scheduled
      multi-pass daily collection (separate item below), since a single manual
      trigger only ever captures one snapshot in time.

### This session — 2026-09-15, part 5 (Hacker News as a non-RSS source)
- [x] Added Hacker News as a new "News API"-category source (per `project.md`'s
      architecture, distinct from RSS/Websites) -- new fetcher
      (`app/sources/hackernews_api.py`) using the official Algolia search API,
      new Celery task (`app/tasks/ingestion_hackernews.py`), new endpoint
      `POST /api/v1/ingestion/hackernews`, credibility weight added
      (`"Hacker News": 0.75`). New dependency: `requests`.
- [x] **Investigated and deliberately dropped GitHub** ("trending" via the
      official Search API proxy -- `topic:artificial-intelligence` +
      `created:>N days` + `sort:stars`). Verified live: repos created
      yesterday top out at 2 stars, repos near a 14-day window's edge top out
      at 16 stars -- nowhere close to real "trending," and structurally
      biased toward obscure repos since the API can only sort by cumulative
      stars, not stars-gained-recently. GitHub has no official trending API
      at all, only unofficial scrapers, which were already ruled out per the
      Anthropic/Meta AI precedent. Not adding GitHub as a source for now --
      revisit only if a genuinely reliable trending signal becomes available.
- [x] Verified Hacker News's actual daily consistency and content quality
      before building (not just once): sampled `points>15` AI stories for
      each of the last 7 individual days -- 19-24 qualifying stories every
      single day, no dry days, many in the 100-1200+ point range on
      substantive topics. Confirmed via a second immediate re-run of
      ingestion that already-stored HN stories are correctly skipped as
      duplicates, not re-surfaced as "new" -- answers "will these repeat
      every day?" directly for the shipped behavior: no. Confirmed with real
      numbers: first run `{'seen': 20, 'inserted': 20, 'duplicates': 0}`,
      immediate second run `{'seen': 20, 'inserted': 0, 'duplicates': 20}`.
      First real run also produced the first-ever cross-source duplicate
      detected all session (an Ars Technica article and an HN story both
      about the same Apple iOS 27 release, 77% title similarity) -- momentum
      had been 0 for every story until this point.

## Known issues / follow-ups

- [ ] Caption timing in `compose_video_task` is a naive proportional estimate
      (sentence character-count share of total audio duration), not real
      forced alignment against the TTS engine's actual word timings --
      captions will drift out of sync on longer/uneven sentences. Real
      alignment is future work.
- [ ] Composed video duration (`ffprobe` on the final mp4) doesn't exactly
      match the source audio duration stored on `story_content` (seen: audio
      29.7s vs muxed video 31.4s) -- likely `-shortest`/keyframe rounding in
      the ffmpeg compose step. Cosmetic, didn't affect playback, not
      root-caused yet.
- [ ] Script/voice/visual/video pipeline is scoped to **one story at a
      time** -- not yet wired up to run across an entire Top-25 episode
      (would need per-episode orchestration, likely a "compose full episode"
      task that fans out to all 25 stories then concatenates/sequences the
      results into one video).

- [ ] `worker` container runs Celery as root (harmless locally, but the image has
      no non-root user — should fix before any production deployment)
- [ ] No automated tests exist yet for ingestion/dedup/ranking logic — all
      verification so far has been manual end-to-end runs against live RSS feeds
- [ ] Two RSS sources are disabled and need real fixes, not just a flag:
      VentureBeat AI (Vercel bot challenge, HTTP 429) and Microsoft AI Blog
      (HTTP 410 Gone, needs a replacement feed URL) — see `app/sources/registry.py`
- [ ] Potential race condition (untested, low likelihood at current scale):
      two concurrent ingestion runs could both pass the per-URL existence
      check before either commits, then collide on the `uq_stories_url`
      constraint — the broad per-source `except Exception` would roll back
      and lose that entire source's batch, not just the colliding row. Only
      matters if ingestion is ever triggered concurrently (not the case with
      a single daily scheduler). See `errors.md` §5.

## Next up (near-term, per architecture but not yet built)

- [ ] Fact Extraction phase (claims, dates, companies, products, events)
- [ ] Verification Engine (cross-source confirmation before a story is
      publishable) — currently the pipeline ranks AI-candidate stories directly,
      with no separate verified/unverified gate
- [ ] Editorial Dashboard (human review of Top 30: edit, reorder, replace
      defective stories with backups, approve/reject)
- [ ] Scheduled collection cycle (10 PM / 1 AM / 3:30 AM IST cutoff) — all
      pipeline stages are currently triggered manually via `curl`

## Future phases (per `project.md`, not started)

- [ ] Script Generation (fact-based script: headline, summary, why it matters, sources)
- [ ] Voice Generation (one branded AI voice)
- [ ] Visual/Asset Engine (avatar, visuals, screenshots, motion graphics, music)
- [ ] Video Composition (voice + visuals + avatar + captions + branding)
- [ ] Automated Video QA (story count, AI-only, sources, captions, audio, duration)
- [ ] Final Human Approval workflow
- [ ] Publishing Worker (YouTube + Instagram)
- [ ] Analytics Worker (views, retention, watch time, shares, likes/comments, followers)
- [ ] Notification Worker (failure alerts)
- [ ] Optimization Engine (feed analytics back into ranking)
- [ ] AWS evolution (EventBridge scheduled jobs, RDS, S3)
- [ ] Kubernetes/EKS evolution
