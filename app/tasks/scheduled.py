from app.tasks.episode_qa import run_episode_qa
from app.tasks.episode_video import produce_episode_video
from app.tasks.ranking import run_ranking_selection
from app.worker.celery_app import celery_app


@celery_app.task
def run_nightly_cutoff(run_date_iso: str | None = None) -> dict:
    """
    The "collection cutoff" step of the daily cycle (project.md's
    Daily Execution Architecture -- 4 AM IST, after the 10 PM/1 AM/
    3:30 AM IST collection passes): rank + select the Top 25 + 5
    backups, produce the full episode video, then run Automated QA.

    Runs all three steps sequentially in-process (calling each task's
    function directly rather than via .delay()) rather than a Celery
    chain, since produce_episode_video needs the specific episode_id
    that run_ranking_selection just created and each step must
    genuinely wait for the previous one to finish -- same rationale as
    _produce_story_content in app/tasks/episode_video.py.

    Stops once the episode is produced and QA'd. Human approval (the
    last step before the 6 AM IST publish target) remains a manual
    dashboard action -- this task doesn't touch Episode.status.
    """

    ranking_result = run_ranking_selection(run_date_iso)
    episode_id = ranking_result["episode_id"]

    produce_result = produce_episode_video(episode_id)
    qa_result = run_episode_qa(episode_id)

    result = {
        "episode_id": episode_id,
        "eligible_stories": ranking_result["eligible_stories"],
        "primary_selected": ranking_result["primary_selected"],
        "backup_selected": ranking_result["backup_selected"],
        "produce_status": produce_result.get("status"),
        "stories_failed": produce_result.get("stories_failed"),
        "backups_failed": produce_result.get("backups_failed"),
        "qa_status": qa_result.get("qa_status"),
    }

    print(f"[scheduled] Nightly cutoff completed: {result}")

    return result
