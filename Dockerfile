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
    && rm -rf /var/lib/apt/lists/*
# ffmpeg: composes the final video from audio + image + captions.
# fonts-dejavu-core: provides the TTF fonts used to render the
# branded visual card (Pillow needs a real font file, not a default).

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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# Start the FastAPI application.
