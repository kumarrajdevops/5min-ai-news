#!/bin/sh
set -e

# media/ is bind-mounted in local dev (docker-compose.yml's `.:/app`),
# which overlays whatever ownership the Dockerfile's build-time chown
# set -- and earlier containers that ran as root before appuser existed
# may have already created root-owned files/directories there. Fix
# ownership every start (idempotent, cheap) before dropping to appuser,
# rather than relying on a one-time manual chown on the host that
# wouldn't survive `docker compose down -v` or a fresh clone.
mkdir -p /app/media
chown -R appuser:appuser /app/media

exec gosu appuser "$@"
