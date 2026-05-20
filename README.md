# AsyncTaskFlow v1.0 — Generic API Task Gateway

A production-ready distributed task processing system that can call any HTTP API asynchronously.

## Quick Start

```bash
cp .env.example .env
# Edit .env to add your API keys
docker compose up -d --build
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## How It Works

1. Register a task type (configure which API to call)
2. Submit a task (provide content + params)
3. Workers process tasks asynchronously
4. Monitor progress via dashboard or SSE

## Register a Task Type

```bash
curl -X POST http://localhost:8000/api/v1/task-types/ \
  -H "Content-Type: application/json" \
  -d '{
    "type_id": "translate",
    "name": "Text Translation",
    "api_base_url": "https://api.example.com",
    "api_endpoint": "/v1/translate",
    "http_method": "POST",
    "auth_type": "bearer",
    "auth_config": {"token": "${TRANSLATE_API_KEY}"},
    "request_template": "{\"text\": \"{{content}}\", \"target\": \"{{params.target_lang | default('en')}}\"}",
    "response_jsonpath": "$.data.translated_text"
  }'
```

## Submit a Task

```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "translate",
    "content": "Hello world",
    "params": {"target_lang": "zh"}
  }'
```

## Check Result

```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

## Architecture

- **API Layer**: FastAPI REST API with task type management
- **Worker Layer**: Celery workers with GenericAPIExecutor
- **Storage**: Redis for queues, task data, and configuration
- **Real-time**: Server-Sent Events for live updates

## Task Type Configuration

Each task type defines:
- API connection (base_url, endpoint, method)
- Authentication (bearer, api_key, basic)
- Request template (Jinja2)
- Response extraction (JSONPath)
- Retry policy (max_retries, retry_on_status, retry_schedule)
- Rate limiting (requests per interval)

## API Endpoints

- `POST /api/v1/task-types/` — Register task type
- `GET /api/v1/task-types/` — List task types
- `GET /api/v1/task-types/{type_id}` — Get task type
- `PUT /api/v1/task-types/{type_id}` — Update task type
- `DELETE /api/v1/task-types/{type_id}` — Delete task type
- `POST /api/v1/task-types/{type_id}/test` — Test task type
- `POST /api/v1/task-types/{type_id}/activate` — Activate task type
- `POST /api/v1/task-types/{type_id}/deactivate` — Deactivate task type
- `POST /api/v1/tasks/submit` — Submit task
- `GET /api/v1/tasks/` — List tasks
- `GET /api/v1/tasks/summaries/` — List task summaries
- `GET /api/v1/tasks/{task_id}` — Task detail
- `POST /api/v1/tasks/{task_id}/retry` — Retry task
- `DELETE /api/v1/tasks/{task_id}` — Delete task
- `GET /api/v1/queues/status` — Queue status
- `GET /api/v1/queues/status/stream` — SSE real-time updates
- `GET /health` — Health check

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Celery result backend |
| `WORKER_REPLICAS` | `3` | Number of worker replicas |
| `CELERY_WORKER_CONCURRENCY` | `2` | Worker concurrency |
| `CELERY_TASK_TIME_LIMIT` | `900` | Task hard time limit (seconds) |
| `CELERY_TASK_SOFT_TIME_LIMIT` | `600` | Task soft time limit (seconds) |
| `MAX_RETRIES` | `3` | Default max retries |
| `DEBUG` | `true` | Debug mode |
| `LOG_LEVEL` | `INFO` | Log level |

## Frontend

The frontend is a React application with:
- **Dashboard**: Real-time queue monitoring, task submission, and worker stats
- **Task Types**: Manage task type configurations (CRUD, test, activate/deactivate)
- **Tasks History**: Browse, filter, and manage tasks with detailed views
- **Tasks Cleanup**: Maintenance tools for orphaned tasks

## Development

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f worker

# Run tests
cd src/api && uv run pytest
```
