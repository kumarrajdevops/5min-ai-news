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

### This session — 2026-09-15, part 6 (HN source-name vs. publisher fix)
- [x] Reviewed `proposal.md` (an externally-authored document) and verified
      every specific claim it made against live Episode 4 data -- all
      accurate, including that a genuine Guardian article was stored with
      `source_name: "Hacker News"` and scored at HN's 0.75 credibility tier
      instead of whatever a Guardian-specific weight would be. Independently
      found one more case: a story titled "...(Not AI Gen)" was classified
      as an AI candidate purely because "AI" appears as a substring in its
      own title (`filter_reason: "Matched: ai"`) -- a separate, smaller issue
      not addressed by this fix, noted here for later.
- [x] Fixed the source-vs-publisher conflation: added
      `app/sources/publisher_resolver.py` (`resolve_publisher(url)`),
      resolving the real publisher from a story's URL domain instead of
      hardcoding `"Hacker News"` for every HN-discovered story.
      `source_type="hackernews"` still marks the discovery channel; genuine
      Ask/Show/Tell HN self-posts still correctly resolve to `"Hacker News"`
      as their real publisher.
- [x] Added credibility weights for the 4 outlets already confirmed present
      in real data: The Guardian (0.85), The Register (0.80), MacRumors
      (0.75), IEEE Spectrum (0.90). Everything else not curated correctly
      falls through to `DEFAULT_CREDIBILITY = 0.60`.
- [x] Added `app/scripts/backfill_hn_publisher.py` (same pattern as the
      existing `backfill_ai_relevance.py`) to re-resolve `source_name` for
      the 13 HN stories already in the database from earlier this session.
- [ ] Not addressed here (deliberately out of scope, noted above): the
      "(Not AI Gen)" false-positive and the much larger taxonomy-redesign
      proposal in `proposal.md` (Major News / Developer Radar / Research &
      Security / Tools sections, event clustering, content-type
      classification) -- a legitimate longer-term direction, needs its own
      dedicated planning pass.

### This session — 2026-09-15, part 7 (full-episode video production)
- [x] Scaled the script/voice/visual/video content pipeline from one story at
      a time to a full episode: new `POST /api/v1/episodes/{id}/produce`
      (`app/tasks/episode_video.py`) runs every primary story through the
      same 4-stage pipeline sequentially and in-process (not via the
      Celery-chained single-story tasks, which auto-chain async and would
      break sequencing), then concatenates the results into one combined
      episode video via `concat_videos()` (`app/content/video_composer.py`).
      Idempotent (stories already `video_ready` are reused, not
      regenerated) and fault-isolated (a failed story is skipped from the
      final video rather than blocking the whole episode).
- [x] Added `Episode.video_path` / `Episode.video_status` columns
      (migration `a7c3d9e1f204`), exposed via `video_url`/`video_status` on
      `GET /api/v1/episodes/{id}` and `/latest`.
- [x] Shared helpers (`get_or_create_content`, `mark_content_failed`) were
      de-underscored in `app/tasks/content.py` and reused directly, rather
      than duplicating the DB-write/error-handling glue in the new task.
- [x] Verified end-to-end on episode 5 (25 primary stories): first run --
      11 newly produced, 14 reused from earlier single-story tests, **0
      failures**, completed in 55s total; combined video valid (h264/aac,
      6:05, 7.4MB, confirmed via `ffprobe`). Re-ran immediately after --
      correctly reused all 25 (`stories_produced: 0, stories_reused: 25`),
      confirming idempotency.
- [x] ~~Still a straight concatenation only -- no intro/outro~~ -- intro/outro
      added, see "part 8" directly below. Transitions/background music
      remain out of scope (see part 8's own note).

### This session — 2026-09-15, part 8 (episode-level intro/outro branding)
- [x] Added narrated intro/outro clips to the combined episode video, so it
      reads as one produced show rather than 25 stitched clips. New
      `generate_branding_card()` (`app/content/visual_generator.py`) --
      same visual style as the per-story card, minus the "Source: " framing
      which doesn't apply here. New `_produce_branding_clip()` helper
      (`app/tasks/episode_video.py`) reuses the existing voice/caption/
      compose pure functions, same as a story's pipeline, just not tied to
      a Story row.
- [x] Intro: "AI Daily 25" + formatted run_date + "Today's Top 25 AI
      Stories", narrated. Outro: "That's all for today's AI Daily 25. See
      you tomorrow.", narrated. Confirmed with the user (simple +
      informative wording, narrated over silent).
- [x] Intro/outro are regenerated on every `/produce` call (not cached like
      story content) -- deliberately simple, since each clip only costs a
      few seconds and there's no new DB state to track staleness.
- [x] Verified end-to-end on episode 5: combined video duration grew from
      365.5s to 378.7s (+13.2s for both clips, reasonable), both card
      images visually confirmed clean and readable, video still valid
      (h264/aac via `ffprobe`).
- [ ] Still no transitions between segments (hard cut only) and no
      background music (deliberately out of scope -- licensing complexity
      for royalty-free audio, not attempted).

### This session — 2026-09-15/16, part 9 (Automated Video QA)
- [x] Built the architecture's Automated Video QA stage (`app/qa/video_qa.py`,
      `app/tasks/episode_qa.py`, `POST /api/v1/episodes/{id}/qa`) --
      implements every checkmark from `project.md`'s QA checklist: story
      count, AI-only, source links, captions present, audio present, video
      integrity, duration target. Each check independently re-verifies real
      state (actual files on disk, real `ffprobe` stream inspection) rather
      than trusting an earlier stage's own success report.
- [x] "Verified sources" is explicitly reported as **not implemented**
      (`passed: None`, doesn't count as a failure) rather than faked as a
      pass -- there's no Verification Engine built yet (see "Next up"
      below). Honest gap, not silently skipped.
- [x] Duration target set to 300s (5 min), from the project's own name
      ("5min-ai-news") and `proposal.md`'s "<5 minute requirement" framing
      -- not tuned to make current episodes pass.
- [x] Verified end-to-end on episode 5: 7/8 checks pass cleanly (story
      count 25/25, AI-only, source links, captions, audio, video integrity
      all real PASS). **duration_target genuinely FAILS** -- 378.7s vs the
      300s target. This is an honest, expected result (not a bug): 25
      stories' worth of narration plus intro/outro naturally runs long
      without per-story time budgeting, exactly the gap `proposal.md`'s
      "episode budgeting / variable story durations" section already
      flagged. Confirms QA is measuring something real, not rubber-stamping.
- [ ] Not addressed here: fixing the duration overage itself (needs
      variable per-story time budgets or fewer/shorter segments -- a
      content-pipeline change, not a QA change) and building the
      Verification Engine so "source_verification" can become a real check.

### This session — 2026-09-16, part 10 (Editorial Dashboard v1)
- [x] Built the first-ever frontend for this project: `app/dashboard/` (vanilla
      HTML/CSS/JS, served via `StaticFiles(html=True)` mounted in `app/main.py`
      -- no new dependencies, no build step). Scoped per `dashboard-proposal.md`
      (externally authored, full "AI News Studio" vision) with the user's
      confirmed decisions: start lightweight, defer YouTube/Instagram/
      analytics/cloud-storage/auth to a later workstream.
- [x] Episode List view + Episode Studio view (video player, Top 30 with
      primary/backup, QA panel, click-rank-to-jump-player, click-title-to-edit).
- [x] New backend endpoints: `PATCH /api/v1/stories/{id}/content` (script
      edit -- correctly resets content status + clears stale audio/image/
      captions/video paths so a later `/produce` regenerates rather than
      reusing stale media), `POST /api/v1/episodes/{id}/reorder`,
      `POST /api/v1/episodes/{id}/swap` (backup <-> primary), `POST
      .../approve`, `POST .../reject`, `GET /api/v1/episodes` (episode list --
      didn't exist before, only `/latest` and `/{id}` did).
- [x] Drag-and-drop reorder/swap uses native HTML5 drag events, no library
      (dnd-kit), per the confirmed "keep interactivity simple so nothing
      complex needs re-engineering if this ever migrates to React" approach.
- [x] **Bug found and fixed during testing:** the `/swap` endpoint's direct
      simultaneous position swap hit the same transient
      `uq_episode_rank_position` unique-constraint collision the `/reorder`
      endpoint had already been built to avoid -- reproduced with a real 500
      error, fixed with the same "move one row out of the real rank range
      first" technique, re-verified working.
- [x] Backend endpoints (PATCH content, reorder, swap, approve, reject, list)
      all verified directly against real data via `curl` -- reorder swapped
      ranks 1/2 correctly, swap exchanged a primary/backup pair correctly
      (after the fix), approve/reject correctly changed `Episode.status`,
      PATCH correctly reset a story's content status and cleared stale paths.
- [x] **Frontend UI click-tested in a real browser** (via `claude-in-chrome`,
      connected this session): Episode List loads and links to Episode
      Studio; video player loads and plays the produced episode 5 video with
      audio/captions; "click rank to jump player" seeks correctly; "click
      title to edit" opens the story edit modal with headline/summary/script
      pre-filled; QA panel renders all check rows. No console errors on
      load. Drag-and-drop reorder verified with real dispatched `DragEvent`s
      (synthetic mouse drag doesn't trigger native HTML5 DnD, so this needed
      actual `DragEvent`/`DataTransfer` objects) -- confirmed the DOM
      reorders and fires `POST /episodes/{id}/reorder` (200), then reverted
      the test reorder back to original order the same way.
- [ ] Minor known gap, not exploitable through normal dashboard usage but
      worth hardening later: `/reorder` doesn't explicitly validate that all
      provided `story_ids` belong to the same `selection_status` group
      (primary or backup) -- the dashboard only ever sends one group's full
      id list, so this doesn't misbehave in practice, but the endpoint would
      accept a mixed list without complaint.
- [ ] Episode-level `video_status`/`qa_status` don't automatically become
      stale after a reorder/swap/script edit -- only the edited story's own
      `content_status` resets. Re-running Produce/QA after any edit is on
      the human, not enforced by the system yet.

### This session — 2026-09-16, part 11 (produce backups too + Produce/QA progress UI + stale-QA indicator)
- [x] `produce_episode_video` (`app/tasks/episode_video.py`) now also produces
      (script/voice/visual/video) the 5 backup stories, best-effort, as a
      second phase that runs only after the primary video is already
      concatenated and marked `ready` -- so a slow/failing backup can never
      delay or block the primary episode. Backups are never appended to
      `video_paths`/the concatenated output. Verified end-to-end on episode
      5: first run produced 4/5 backups (1 was already `video_ready` from
      earlier testing) in 18.6s total; immediate re-run correctly reused all
      5 (`backups_produced: 0, backups_reused: 5`) in 5.7s, confirming
      idempotency. Confirmed a swap of a now-`video_ready` backup into
      primary needs no regeneration (`story_content.updated_at` unchanged
      by the swap) -- the actual goal of this change.
- [x] Added `Episode.video_produced_at` / `Episode.qa_run_at` (migration
      `c3f7a1d92e58`), set by `produce_episode_video` (success path only)
      and `run_episode_qa` respectively. Exposed via `_serialize_episode`.
      Verified via curl: `video_produced_at` set on produce, `qa_run_at`
      set (and later than `video_produced_at`) after running QA.
- [x] Dashboard: **Produce** button now disables and shows a live `m:ss`
      elapsed timer while queued, polling `GET /episodes/{id}` every 3s
      until `video_status` leaves `"producing"`, then auto-refreshes the
      studio view -- replaces the old "click Produce, refresh yourself in a
      bit" alert. Resumes automatically on page reload if `video_status` is
      still `"producing"` (elapsed timer restarts from reload time in that
      case -- no true start time is persisted, noted as an accepted
      approximation). **Run QA** button got the same treatment (poll every
      1.5s comparing fresh `qa_run_at` against the click time, 30s safety
      timeout), replacing the old blind `setTimeout(2500)`.
- [x] **Run QA** button now shows an amber "stale" state (`Run QA ⚠
      (stale)`, `.btn-warn` style reusing the existing `--skip` palette
      tokens) whenever `video_produced_at > qa_run_at` (or QA has never
      run) -- i.e. whenever Produce has completed since QA last ran.
      Deliberately scoped to Produce only, per what was asked; reorder/
      swap/script-edit still don't invalidate `qa_status` (pre-existing
      gap, unchanged here -- see below).
- [ ] **Not click-tested in a real browser this session** -- the
      claude-in-chrome MCP connection dropped mid-session and couldn't be
      re-established. All of the above was verified via curl/DB queries
      (timestamps, idempotency counts, swap behavior) and a careful
      line-by-line review of the `app.js` diff, plus confirming the served
      `/dashboard/app.js` reflects the new code -- but the actual spinner/
      timer/stale-button rendering and behavior in a live browser needs a
      human click-through before trusting the UI layer specifically.
- [x] **Bug found and fixed (user-reported, real click-through):** swapped a
      backup into primary rank 1, clicked Produce -- timer showed "3 secs"
      then refreshed showing the OLD video, unchanged. Root cause: `POST
      .../produce` only queued the Celery task and returned immediately;
      `episode.video_status` only flips to `"producing"` inside the task
      itself, a moment after the worker picks it up. The dashboard's poll
      stops as soon as `video_status !== "producing"` -- which can't tell
      "hasn't started yet" apart from "already finished". If the first poll
      (fired 3s after click) landed before the worker flipped the status,
      it read the stale pre-produce value, wrongly concluded production was
      already done, and re-rendered the still-old video while the real
      production kept running unseen in the background. Fixed by setting
      `episode.video_status = "producing"` synchronously in the `/produce`
      endpoint itself, before queuing the task (`app/main.py`), closing the
      race by construction. Verified: `video_status` now reads
      `"producing"` immediately on the POST response and stays that way for
      the full first few seconds (checked at t=0/1/3s); reproduced the
      exact scenario (swap backup to primary rank 1, Produce) and confirmed
      the combined video's duration changed and the API's reported rank-1
      story matched the swap -- then reverted the test swap/re-produce to
      restore episode 5's original state.
      Note: the QA polling (`qa_run_at` timestamp comparison) does not have
      this bug -- it compares against a fresh monotonic timestamp captured
      at click time, not a transient status word, so there's no equivalent
      "not started vs. already done" ambiguity.
- [x] **User reported the exact same symptom again after the fix above** --
      investigated further (still couldn't get claude-in-chrome reconnected
      to click-test live, see below). Found and closed a second real gap:
      `GET /media/videos/episode_N.mp4` was served with `Last-Modified`/
      `ETag` but **no `Cache-Control` header at all** -- since the file is
      regenerated in place at the same fixed URL every Produce run (no
      content-hashed filename), a browser could apply heuristic freshness
      and reuse a stale cached copy of the video without ever revalidating
      against the server. Added `RevalidateStaticFiles` (`app/main.py`), a
      thin `StaticFiles` subclass that sets `Cache-Control: no-cache` on
      every `/media` response -- keeps the free conditional-GET/304 fast
      path but forces revalidation every time, so a changed ETag is never
      masked by a stale hit. Also added a small `no_store_api_responses`
      middleware setting `Cache-Control: no-store` on all `/api/*`
      responses, to remove any remaining doubt about the dashboard's
      polling loop ever being satisfied from a cached JSON response
      (these had no validators to begin with, so unlikely to have been
      cached, but cheap to rule out explicitly). Verified via curl: both
      headers now present (`no-cache` on `/media/videos/episode_5.mp4`,
      `no-store` on `/api/v1/episodes/5`).
- [x] **User confirmed after retesting:** the story order/content itself
      now correctly updates after Produce (the two fixes above worked) --
      but the automatic re-render after Produce completes (button resets
      to normal on its own) still showed the OLD video; only a full manual
      page refresh showed the new one. Since the button resetting proves
      the poll->re-render cycle really did run a fresh fetch+DOM rebuild
      (ruling out the earlier race and the missing-Cache-Control-header
      issue, both already fixed), this pointed to a *different*, narrower
      cause: browser `<video>` elements stream via HTTP range requests
      (confirmed `accept-ranges: bytes` on the response), and browsers are
      known to keep serving stale cached video segments under an unchanged
      URL even with correct `Cache-Control` headers, because range-request
      caching is handled by a separate media-cache pipeline that doesn't
      always honor the same revalidation rules as a normal fetch.
- [x] **Fixed properly via cache-busting** (the standard, bulletproof fix
      for this class of bug -- sidesteps the media-cache question
      entirely instead of fighting it): added `Episode.video_produced_at`
      (already existed, from Part 11 above) as a `?v=` query-string suffix
      on the episode player's `src` (`cacheBust()` helper, `app.js`), so a
      real Produce always yields a URL the browser has never seen before.
      Applied the same treatment to each story's edit-panel preview video
      -- added `content_updated_at` to `_serialize_episode`'s per-story
      entry (`app/main.py`) and used it the same way, since a script edit
      -> re-Produce regenerates that story's video at the same fixed
      per-story URL and would hit the identical bug. Verified via curl:
      `video_produced_at`/`content_updated_at` are present in the API
      response, and the video route still resolves correctly with a
      `?v=...` suffix (query strings are ignored by StaticFiles routing,
      200 OK).
- [ ] **Still not click-tested live in a real browser this session** --
      claude-in-chrome remains unavailable (retried twice, no matching
      tools both times). Everything above verified via curl/DB checks
      plus confirming the served `/dashboard/app.js` reflects the new
      code. The user's own live retest (not this session's browser tool)
      is what actually diagnosed the button-resets-but-video-stale
      symptom that led to this fix -- please retest once more on your end
      to confirm the cache-busted URL resolves the remaining issue.

### This session — 2026-09-16, part 12 (source article link per story)
- [x] Added a source-article link below each story's title/source in the
      Top 30 list (`app/dashboard/app.js`'s `renderStoryList`), using the
      already-exposed `story.url` field. Opens in a new tab (`target=
      "_blank" rel="noopener noreferrer"`) so an editor can proofread the
      generated script against the original article without losing their
      place in the dashboard. Click on the link stops event propagation
      so it doesn't also trigger the row's existing "click to edit script"
      handler. No backend changes needed -- `url` was already in
      `_serialize_episode`'s per-story response.
- [x] **Follow-up (same session):** added the same source link to the edit
      panel too (it was missing there), and changed both places to show
      the actual URL text itself (selectable/copyable, not just an arrow
      icon) plus a one-click **Copy** button, so an editor can grab the
      link to share it elsewhere -- not just open it. Shared via one
      `renderSourceLinkHtml()`/`wireSourceLinkCopyButtons()` pair
      (`app.js`) used in both `renderStoryList` and `openEditPanel`; new
      `#edit-source` container added to `index.html`, right above the
      Headline field. Uses `navigator.clipboard.writeText()` with a
      fallback alert showing the raw link if the clipboard API is
      unavailable/denied.
- [x] **Correctness fix caught during review:** `escapeHtml()` escapes
      `&`/`<`/`>` (safe for text nodes) but not `"`, so its output isn't
      safe to embed inside an HTML attribute value -- this is the first
      place in the dashboard doing that (`href="..."`, `data-url="..."`).
      Added a dedicated `escapeAttr()` (escapeHtml + quote-escaping) and
      used it for both attributes, closing a latent HTML-injection risk if
      a story's URL (sourced from external RSS/API feeds) ever contained a
      literal `"` character.

### This session — 2026-09-16, part 13 (edit panel metadata)
- [x] Added a Source/Author/Published/Collected metadata block to the edit
      panel, right below the source-article link (`#edit-meta`, a `<dl>`
      in `index.html`; `renderEditMetaHtml()`/`formatDateTime()` in
      `app.js`). `published_at` and `source_name` were already exposed by
      the API; added `author` and `collected_at` ("when we took it") to
      `_serialize_episode`'s per-story entry (`app/main.py`) since those
      weren't returned before. Dates formatted via
      `toLocaleString()` for readability; missing values (author is often
      null) render as "—" rather than blank/undefined.

### This session — 2026-09-16, part 14 (discovery channel vs. resolved publisher)
- [x] Added a conditional "Discovered via" row to the edit panel's
      metadata block, linking back to the actual discovery page -- e.g. a
      story surfaced via Hacker News but published elsewhere now shows
      both "Source: nathannaveen.dev" (the resolved publisher, from
      `resolve_publisher()` -- see part 6) AND "Discovered via: Hacker
      News ↗" linking to `https://news.ycombinator.com/item?id={hn_id}`.
      New `_discovery_info()` helper (`app/main.py`) returns this only
      when `source_type == "hackernews"`; `None` (row omitted) for
      directly-ingested RSS stories, which have no separate discovery
      channel to show. Verified via the live API: a real HN-discovered
      story returns the expected `{"label": "Hacker News", "url": "...
      item?id=49697477"}`, a plain RSS story returns `discovery: None`.
      Written generically (keyed off `source_type`, not hardcoded to HN)
      so a future non-RSS aggregator source only needs one more branch
      in `_discovery_info()`, not dashboard changes.

### This session — 2026-09-16, part 15 (Produce was silently discarding edited scripts)
- [x] **Critical bug found and fixed, user-reported:** edited story #46's
      summary/script in the dashboard, clicked Save, clicked Produce --
      the video used the OLD auto-generated text, and reopening the edit
      panel showed the OLD text again too, as if the edit never happened.
      Root cause: `_produce_story_content()` (`app/tasks/episode_video.py`,
      used by episode-level Produce) unconditionally called
      `generate_script()` from the story's original RSS title/summary on
      **every** call, regardless of whether a script already existed --
      silently overwriting a human-edited script (which the edit panel's
      `PATCH /stories/{id}/content` deliberately preserves, only clearing
      the downstream audio/image/captions/video to force those to
      regenerate *from* the edit) with the auto-generated template text.
      The edit panel then correctly displayed whatever was actually in
      the DB -- which was the just-clobbered auto text, not a caching or
      rendering bug on the frontend.
- [x] Fixed by skipping script (re)generation whenever
      `content.script_text` is already populated -- covers both the
      edit-preservation case and, as a side benefit, a retry after a
      failure at the voice/visual/video stage (no longer wastefully/
      riskily redoes script generation it didn't need to). Applied the
      identical fix to `generate_script_task`
      (`app/tasks/content.py`, the single-story `POST /stories/{id}/produce`
      path) since it had the exact same unconditional-regeneration bug,
      even though the dashboard doesn't call that endpoint directly.
- [x] Verified end-to-end by reproducing the user's exact report: PATCHed
      story 46 with their exact summary/script text, confirmed the PATCH
      response showed `status: script_ready`; triggered episode 5's
      Produce; confirmed after completion that `GET /stories/46/content`
      still shows the **exact edited text** in both `summary` and
      `script_text`, `status: video_ready`, and a fresh `audio_duration_seconds`/
      `video_url`/`updated_at` -- proving voice/visual/video were correctly
      regenerated *from* the edited script, not from a re-run of the
      auto-generator.

### This session — 2026-09-16, part 16 (edit panel Close button placement)
- [x] Moved the edit panel's Close button from the header's top-right into
      the footer, right after Save (`index.html`/`style.css`) -- no JS
      changes needed, same `#edit-close` element/id, just repositioned.

## Known issues / follow-ups

- [ ] Reorder/swap/script-edit still don't mark `qa_status`/the new
      staleness fields as stale -- only a completed Produce does (see part
      11 above). Broadening this to reorder/swap/edit wasn't asked for yet;
      revisit if it turns out to matter in practice.

- [ ] Observed during dashboard click-testing: 1 of 25 stories in episode 5
      (story #28, NVIDIA Blog) has script text "No summary was available
      from the source." -- confirmed isolated (only 1 row across all of
      `story_content` matches this), not investigated further since it's a
      single-source RSS gap, not a UI or pipeline bug.

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
- [x] ~~Script/voice/visual/video pipeline is scoped to one story at a time~~
      -- resolved, see "part 7 (full-episode video production)" above.

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

## Future phases (per `project.md`)

Script/Voice/Visual/Video are now built in simplified/free form, at
full-episode scale, with episode branding -- see parts 5-8 above.
Noting here what's still genuinely missing from each, since the
original `project.md` description was broader than what's built:

- [~] Script Generation -- deterministic headline + summary only, no
      LLM/fact-extraction, no "why it matters" (deliberately removed
      per user direction), no explicit source citation in the spoken
      narration (source is shown on-screen in the visual card only).
- [x] Voice Generation -- one branded AI voice (edge-tts), as designed.
- [~] Visual/Asset Engine -- static branded title cards only. No avatar,
      no screenshots, no motion graphics, no background music.
- [~] Video Composition -- voice + visuals + captions + episode-level
      branding (intro/outro) all working. No avatar, no transitions.
- [ ] Automated Video QA (story count, AI-only, sources, captions, audio, duration)
- [ ] Final Human Approval workflow
- [ ] Publishing Worker (YouTube + Instagram)
- [ ] Analytics Worker (views, retention, watch time, shares, likes/comments, followers)
- [ ] Notification Worker (failure alerts)
- [ ] Optimization Engine (feed analytics back into ranking)
- [ ] AWS evolution (EventBridge scheduled jobs, RDS, S3)
- [ ] Kubernetes/EKS evolution

### Design principle for the future taxonomy/categorized-episode work

From `proposal.md` (see the taxonomy-redesign item above, not yet
scheduled) -- worth preserving on its own since it reframes what
"Top 25" even means, independent of whether/when the fuller
Major-News/Developer-Radar/Research/Tools redesign gets built:

> The 25 is a **daily information budget**, not a claim that 25 major
> news events happened. Some days: 9 major news + 4 research + 3
> security + 7 developer + 2 public impact = 25. Other days: 15 major
> news + 4 research + 3 security + 3 developer = 25. Other days: 6
> major news + 3 research + 2 security + 8 developer + 6 tools = 25.
> All three are "perfect" -- none is a shortfall.

Why this matters for this project specifically: it's the design
answer to "will we ever run out of 30 stories/day?" (the question
that originally motivated expanding sources to Hacker News, RSS
additions, etc. -- see the RSS/HN expansion notes above). Treating
research/security/developer/tool content as legitimate, differently-
weighted budget categories rather than diluted "news" means a quiet
major-news day doesn't have to mean an under-filled or padded-with-
junk episode -- Hacker News alone reliably supplies 19-24 qualifying
items/day (verified this session) across exactly these categories.
This only pays off once content-type classification and per-category
ranking exist (part of the larger taxonomy redesign, not built yet) --
recorded here now so the principle isn't lost before that work starts.
