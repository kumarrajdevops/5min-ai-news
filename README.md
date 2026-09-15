# AI News Platform

Local-first MVP for a daily Top 25 AI technology news video.

Current slice:
- FastAPI API
- PostgreSQL
- Redis
- Celery worker
- RSS source ingestion
- SQLAlchemy persistence
- Docker Compose
- Manual ingestion endpoint

## Start

```bash
docker compose up --build
```

API:
http://localhost:8000

Health:
http://localhost:8000/health

OpenAPI:
http://localhost:8000/docs

Trigger RSS ingestion:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/rss
```

Check collected stories:

```bash
curl http://localhost:8000/api/v1/stories
```

Stop:

```bash
docker compose down
```

Reset database:

```bash
docker compose down -v
```
