AI News Platform (5min-ai-news) -- Test Run Findings
Date: 2026-09-15
Tested by: docker compose up --build -d, then exercising the full
pipeline (alembic upgrade head -> /health -> ingestion -> dedup ->
episode selection) against a completely fresh environment.

====================================================================
1. CRITICAL -- Alembic migration chain has no baseline "create
   stories table" migration. Fresh DB cannot be initialized at all.
====================================================================

Command:
    docker compose exec api alembic upgrade head

Result: FAILS immediately on the very first migration.

    Running upgrade  -> 996b16094585, add ai relevance fields
    sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
    relation "stories" does not exist
    [SQL: ALTER TABLE stories ADD COLUMN ai_relevance VARCHAR(50)]

Root cause:
    alembic/versions/996b16094585_add_ai_relevance_fields.py is the
    first migration in the chain (down_revision = None), but it only
    does `op.add_column("stories", ...)`. There is no earlier
    migration that does `op.create_table("stories", ...)`. The two
    later migrations (a1f92e6d7b3c_add_dedup_fields.py,
    c7d3f8a91b42_add_episodes.py) both also assume `stories` already
    exists.

    This strongly suggests the `stories` table used to be created via
    SQLAlchemy's `Base.metadata.create_all()` during earlier
    development, and when that call was intentionally removed from
    app/main.py / app/db.py (per the docstring in app/main.py
    explaining why create_all() and Alembic must not both manage
    schema), no one ever generated the missing baseline migration to
    replace it. Confirmed: on a totally fresh Postgres volume,
    `\dt` shows zero tables, and even `alembic_version` itself is
    never created because the first migration fails inside a
    transactional DDL block and rolls back.

Impact: BLOCKS EVERYTHING. With no `stories` table, every endpoint
that touches data fails:
    - POST /api/v1/ingestion/rss -> ingestion runs, RSS feeds fetch
      fine, but every single article fails to insert:
        psycopg.errors.UndefinedTable: relation "stories" does not
        exist
      (fails identically for every enabled source: TechCrunch AI,
      The Verge AI, MIT Technology Review AI, NVIDIA Blog, etc.)
    - POST /api/v1/dedup/run -> same UndefinedTable error
    - POST /api/v1/episodes/select -> same UndefinedTable error
    - GET  /api/v1/stories -> 500 Internal Server Error (same root
      cause, relation "stories" does not exist)

Only /health succeeds, because it only does `SELECT 1`, not a real
table query.

Fix needed: add a new baseline migration (revision 0, before
996b16094585) that creates the `stories` table with the ORIGINAL
column set (title, url, source_name, source_type, published_at,
collected_at, updated_at, author, external_id, raw_summary,
raw_content, content_hash, status, uq_stories_url), then re-point
996b16094585's down_revision at it. Without this, `alembic upgrade
head` can never succeed on a clean database -- which is the ONLY
supported setup path per README.md's "First-time setup" section.

====================================================================
2. Docker Compose project-name / volume mismatch (FIXED during this
   session)
====================================================================

docker-compose.yml had `name: ai-news-platform` pinned, but the
actual dev/repo project name is `5min-ai-news` (confirmed by the
user) and pre-existing containers/volumes on this machine were all
under the `5min-ai-news_*` prefix. Left as-is, every future
`docker compose up` would have silently created a brand new, empty
`ai-news-platform_postgres_data` volume instead of reusing the real
one -- exactly the data-loss scenario the comment above `name:` was
trying to prevent, just triggered by the pin itself pointing at the
wrong name.

Fix applied in this session:
    - docker-compose.yml: `name: ai-news-platform` -> `name: 5min-ai-news`
    - README.md: added a naming note -- repo/dev project name is
      `5min-ai-news`; "AI News Platform" is the production/public
      brand name for the same project.

Leftover cleanup (not done automatically -- destructive, needs
confirmation): an empty, unused `ai-news-platform_postgres_data`
Docker volume was created earlier in this session before the rename
and is now orphaned. Safe to remove with:
    docker volume rm ai-news-platform_postgres_data
(Only after confirming no one wants to keep testing against it --
it never received any data.)

====================================================================
3. Everything else checked out
====================================================================

- docker compose up --build -d: builds and starts cleanly (api,
  worker, postgres, redis all healthy).
- GET /health: 200 OK, {"status":"ok","service":"ai-news-api"}.
- Celery worker connects to Redis and registers all 3 tasks fine.
- RSS ingestion itself (feed fetch + parse + AI-relevance
  classification logic) works correctly up until the DB insert --
  e.g. TechCrunch AI returned 20 entries, The Verge AI 10, MIT Tech
  Review 10, NVIDIA Blog 18, all with HTTP 200. The two
  intentionally-disabled sources (VentureBeat AI, Microsoft AI Blog)
  were correctly skipped, matching the documented reasons in
  app/sources/registry.py.
- worker container prints a harmless root-user warning at startup
  ("Please specify a different user using the --uid option") --
  celery running as root inside the container. Not blocking for
  local dev, but worth a non-root user in Dockerfile before any
  production use.

====================================================================
Recommended next step
====================================================================
Generate/add the missing baseline "create stories table" Alembic
migration (see #1), re-run `alembic upgrade head`, then re-test the
full ingestion -> dedup -> episode-selection chain end to end.

====================================================================
UPDATE 2026-09-15 -- Fix #1 applied and verified
====================================================================

Added alembic/versions/6f1e2a7b9c04_create_stories_table.py as the
new baseline migration (down_revision=None), creating `stories` with
the exact pre-996b16094585 column set (title, url, source_name,
source_type, published_at, collected_at, updated_at, author,
external_id, raw_summary, raw_content, content_hash, status,
uq_stories_url). Re-pointed 996b16094585's down_revision from None
to "6f1e2a7b9c04".

Verified chain with `alembic history`:
    <base> -> 6f1e2a7b9c04 -> 996b16094585 -> a1f92e6d7b3c
    -> c7d3f8a91b42 (head)

`alembic upgrade head` now succeeds cleanly on a fresh database, all
4 tables created (alembic_version, stories, episodes,
episode_stories).

Full pipeline re-tested end to end and confirmed working:
    - POST /api/v1/ingestion/rss: 8 sources processed, 2153 articles
      seen, 26 inserted (rest correctly filtered as outside the
      22h collection window), 0 failures.
    - Dedup auto-chained: 16 stories checked, 0 duplicates (expected
      -- first run, nothing to dedup against yet).
    - GET /api/v1/stories: returns real classified stories with
      correct ai_relevance/score/filter_reason.
    - POST /api/v1/episodes/select + GET /api/v1/episodes/latest:
      episode created, all 16 AI-candidate stories ranked and scored
      (recency/credibility/ai_relevance/momentum breakdown per
      story), correctly placed as 16 primary / 0 backup since fewer
      than 30 candidates existed -- no forced padding to 25+5.

Item #1 is resolved. Item #2 (naming) was already fixed in the prior
session. The orphaned `ai-news-platform_postgres_data` volume has
since been removed.

====================================================================
4. NEW -- POST /api/v1/episodes/select silently accepts an invalid
   run_date and fails asynchronously with no error surfaced to the
   caller
====================================================================

Command:
    curl -X POST "http://localhost:8000/api/v1/episodes/select?run_date=not-a-date"

Result: HTTP 200, {"task_id": "...", "status": "queued"} -- looks
like success to the caller. The actual failure only shows up in the
Celery worker logs, several seconds later, with no way for the API
caller to know it happened:

    ValueError: Invalid isoformat string: 'not-a-date'
    File "/app/app/tasks/ranking.py", line 38, in run_ranking_selection
        run_date = date.fromisoformat(run_date_iso)

Root cause: `trigger_ranking_selection()` in app/main.py takes
`run_date: str | None` with no format validation, and hands it
straight to `run_ranking_selection.delay(run_date)`. Celery tasks run
out-of-process, so an unhandled exception there never reaches the
HTTP response -- the request has already returned 200 by the time the
task even starts.

Impact: LOW severity (no data corruption -- confirmed the crash
happens before the task opens a DB session, so no partial Episode row
is created; verified via `SELECT * FROM episodes` after triggering
this). But it's a real UX/reliability gap: a typo'd run_date (e.g.
from a future Editorial Dashboard or script) fails completely silently
from the caller's point of view.

Suggested fix: validate `run_date` in the endpoint itself (e.g.
`date.fromisoformat()` inside a try/except, returning HTTP 422 with a
clear message) before calling `.delay()`, rather than deferring the
parse to the worker.

UPDATE 2026-09-15 -- FIXED. `trigger_ranking_selection()` in
app/main.py now validates `run_date` with `date.fromisoformat()`
before queuing the task, raising `HTTPException(422)` with a clear
message on bad input. Verified:
    - run_date=not-a-date -> 422 {"detail":"Invalid run_date
      'not-a-date'; expected YYYY-MM-DD."}
    - run_date=2026-09-15 -> 200, queued normally
    - omitted -> 200, queued normally (defaults to today)
No errors in worker logs after the fix.

====================================================================
5. Stability check -- 2026-09-15 (this session)
====================================================================

Re-verified after fix #1, with the stack left running ~15 minutes
under normal use (repeated ingestion/dedup/ranking triggers):

- All 4 containers (api, worker, postgres, redis) remained healthy
  the whole time, no restarts or crash loops.
- Re-running ingestion is correctly idempotent: second run saw the
  same 2153 articles, inserted 0 new (all 26 previously-inserted
  correctly recognized as existing via the `uq_stories_url`
  constraint check), no errors.
- Re-running dedup is stable: 16 checked / 0 duplicates both times,
  consistent with an unchanged canonical pool.
- 404 handling verified correct: GET /api/v1/episodes/99999 ->
  404 {"detail": "Episode not found."}
- GET /api/v1/stories/{id}/duplicates on a nonexistent story_id
  returns 200 with an empty list rather than 404 -- not a bug, but
  worth knowing: this endpoint can't distinguish "story exists with
  no duplicates" from "story doesn't exist at all."
- limit query param clamping on GET /api/v1/stories confirmed
  correct at both ends (limit=-5 clamped to 1, limit=99999 clamped
  to 100).
- Found and documented bug #4 above (invalid run_date).

Not tested (would require orchestrating real concurrency): a race
condition where two ingestion runs triggered back-to-back close
enough together could both pass the "does this URL already exist"
check before either commits, then both attempt to insert the same
URL -- the per-source `db.commit()` would raise an IntegrityError on
`uq_stories_url`, caught by the broad `except Exception` per source,
rolling back and losing that entire source's batch for that run (not
just the colliding row). Low real-world likelihood given the
pipeline is meant to run on a schedule, not be triggered concurrently
by multiple callers, but worth knowing if a scheduler or retry logic
is added later.

Overall verdict: with fix #1 applied, the current implemented slice
(ingestion -> dedup -> ranking/episode selection) is stable for local
MVP use. No crashes, no data corruption, no memory/resource issues
observed. Bug #4 is the only outstanding functional issue found.
