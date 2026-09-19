# One-time interactive script to obtain a YouTube Data API v3 refresh
# token for the Publishing Worker (app/tasks/publishing.py). Celery
# workers run headless and can't complete an interactive OAuth consent
# flow themselves -- this script does it once, on a machine with a real
# browser, and prints the resulting refresh token to paste into .env.
#
# Run this on your HOST machine, not inside a Docker container --
# it opens a real browser window, which a container can't do:
#   pip install google-auth-oauthlib google-api-python-client google-auth
#   python -m app.scripts.youtube_oauth_setup
#
# Before running, you need a Google Cloud OAuth client (see README.md's
# Publishing section for the full setup): a Cloud project with the
# YouTube Data API v3 enabled, an OAuth consent screen configured, and
# an OAuth Client ID of type "Desktop app". Put its client_id/secret in
# .env as YOUTUBE_CLIENT_ID/YOUTUBE_CLIENT_SECRET before running this.

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def run_oauth_setup() -> None:
    if not settings.youtube_client_id or not settings.youtube_client_secret:
        print(
            "YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET must be set in .env "
            "before running this script -- see README.md's Publishing section."
        )
        return

    from google_auth_oauthlib.flow import InstalledAppFlow

    client_config = {
        "installed": {
            "client_id": settings.youtube_client_id,
            "client_secret": settings.youtube_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    # Opens your default browser for the Google consent screen and
    # runs a temporary local server to catch the redirect.
    credentials = flow.run_local_server(port=0)

    print("\nSuccess. Add this line to .env:\n")
    print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}\n")


if __name__ == "__main__":
    run_oauth_setup()
