FROM python:3.12-slim
# Use Python 3.12 as the application runtime.

WORKDIR /app
# All application commands will execute from /app.

ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from creating .pyc files.

ENV PYTHONUNBUFFERED=1
# Make Python logs appear immediately in Docker logs.

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    gosu \
    && rm -rf /var/lib/apt/lists/*
# ffmpeg: composes the final video from audio + image + captions.
# fonts-dejavu-core: provides the TTF fonts used to render the
# branded visual card (Pillow needs a real font file, not a default).
# gosu: lets entrypoint.sh start as root (needed to fix media/'s
# ownership on every start -- see entrypoint.sh) and then drop to
# appuser for the actual long-running process, rather than the
# container running entirely as root.

COPY requirements.txt .
# Copy Python dependencies into the image.

RUN pip install --no-cache-dir -r requirements.txt
# Install the application dependencies.

COPY app ./app
# Copy the application source code.

COPY alembic ./alembic
# Copy the Alembic migration environment and migration files.

COPY alembic.ini ./alembic.ini
# Copy the Alembic configuration file.

COPY .env.example ./.env.example
# Copy the example environment configuration.

RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
# Non-root user -- the image previously ran api/worker as root,
# harmless locally but a real hardening gap before any production
# deployment. This chown covers the image's own baked-in files (what a
# real, non-bind-mounted deployment actually runs); in local dev the
# bind mount (.:/app) overlays it, which is what entrypoint.sh's
# runtime chown handles instead.

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Runs as root (fixes media/'s ownership -- see entrypoint.sh's own
# comment for why that's needed even after the chown above), then
# drops to appuser via gosu before exec'ing the actual command. The
# long-running application process (uvicorn/celery/beat) always ends
# up running as appuser, never root.
ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Start the FastAPI application.
