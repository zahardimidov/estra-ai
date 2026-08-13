# EstraAI

Async content moderation API — detect spam, toxicity, scam, and NSFW content via REST, built for startups that need moderation without training their own models.

`Python` · `FastAPI` · `PostgreSQL` · `Redis` · `Docker Compose` · `Prometheus` · `Grafana`

---

## Overview

EstraAI is an asynchronous REST API for text and image moderation.

A client submits content and immediately receives a `task_id`. A worker later processes the task and stores the result in the database. Clients can poll `GET /v1/tasks/{id}` or provide a webhook URL.

The current classifiers are simple keyword-based stubs for spam, scam, toxicity, and NSFW detection. They are intentionally basic: this project focuses on the API, queue, worker flow, authentication, rate limiting, and monitoring around a moderation model.

Layered architecture (API / domain / infrastructure), a Unit-of-Work pattern over SQLAlchemy, and a repository per aggregate keep business logic independent of FastAPI and the database driver — swapping SQLite for Postgres, or the keyword-stub scorer for a real model, touches one layer at a time.


## How it works

```
POST /v1/moderate/text
        │
        ▼
   API validates → creates task → pushes task_id to Redis
        │
        ▼
   Worker pops task → runs ML inference → saves result to DB
        │
        ├── GET /v1/tasks/{id}   ← client polls
        └── POST callback_url    ← webhook (optional)
```

The API returns `202` with a `task_id` immediately; a separate worker process does the actual scoring in the background. Submission and processing scale independently, so `docker compose up --scale worker=3` adds throughput without touching the API.

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (async) |
| Queue | Redis (LPUSH/BRPOP) |
| Database | PostgreSQL / SQLite (local) |
| Object storage | MinIO (S3-compatible) |
| Auth | JWT + API keys |
| Observability | Prometheus + Grafana |
| Reverse proxy | nginx |
| ML | Keyword-based stubs, swappable per category (v0.1) |
| Infra | Docker Compose |

---

## Quickstart (local, SQLite)

```bash
# 1. Install dependencies
uv sync --extra dev

# 2. Create .env in backend/
cp backend/.env.example backend/.env

# 3. Run Redis + MinIO (needed for the queue and image uploads)
docker compose up -d redis minio

# 4. Run API (from backend/)
cd backend
uvicorn main:app --reload

# 5. Run worker (separate terminal, from backend/)
python -m workers.worker
```

API is available at `http://localhost:8000`, interactive docs at `http://localhost:8000/docs`.

Postgres can be swapped in too (`docker compose up -d postgres` + set `ENGINE` in `.env`) — SQLite is just the zero-setup default for local dev.

## Quickstart (Docker)

```bash
# Start all services
docker compose up -d --build

# Scale workers
docker compose up -d --scale worker=3

# Scale the API — nginx load-balances across replicas
docker compose up -d --scale api=3
```

Services started: `api`, `worker`, `postgres`, `redis`, `minio`, `prometheus`, `grafana`, `nginx`.

| Service | URL |
|---|---|
| API (via nginx) | http://localhost:80 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 (anonymous viewer access, or `admin`/`admin`) |
| MinIO console | http://localhost:9001 |

`api` has no host port of its own — nginx is the only entry point into it. That's what makes `--scale api=N` actually work: a fixed host-port mapping (the old `8000:8000`) can't be shared by multiple containers, so as long as `api` published one directly, only a single replica could ever run. nginx re-resolves `api`'s hostname on every request via Docker's embedded DNS instead of caching one IP at startup (see [infra/nginx/nginx.conf](infra/nginx/nginx.conf)), so it round-robins across however many replicas are up.

Grafana comes pre-provisioned with a Prometheus datasource and an "EstraAI Overview" dashboard (request rate/latency, queue size, inference latency, blocked ratio) — no manual setup needed.

Prometheus itself has no service discovery for scaled replicas in plain Docker Compose, so with `--scale worker=N` its `worker` target only ever reaches one replica at a time.

---

## API

### Auth

```http
POST /v1/auth/sign-up
Content-Type: application/json

{ "email": "user@example.com", "password": "Pass1!", "password_repeat": "Pass1!" }
```

```http
POST /v1/auth/sign-in
Content-Type: application/json

{ "email": "user@example.com", "password": "Pass1!" }

→ { "token": "<jwt>" }
```

### Moderation

```http
POST /v1/moderate/text
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "Buy crypto now and earn 1000$/day!",
  "categories": ["spam", "scam", "toxicity"],  // default: all three
  "callback_url": "https://your-service.com/webhook"  // optional
}

→ 202 { "task_id": "...", "status": "pending" }
```

```http
GET /v1/tasks/{task_id}
Authorization: Bearer <token>

→ {
    "task_id": "...",
    "status": "completed",
    "decision": "blocked",
    "scores": { "spam": 0.91, "scam": 0.74, "toxicity": 0.08 },
    "model_versions": { "spam": "0.1.0-stub", "scam": "0.1.0-stub", "toxicity": "0.1.0-stub" },
    "categories": ["spam", "scam", "toxicity"],
    "created_at": "...",
    "completed_at": "..."
  }
```

```http
POST /v1/moderate/image
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=<binary>&categories=nsfw

→ 202 { "task_id": "...", "status": "pending" }
```

Images are uploaded to S3-compatible storage (MinIO) before the task is queued; the worker runs the same async pipeline as text.

**Decision logic:** `blocked` if any category score ≥ 0.7, otherwise `approved`.

**Categories:** `spam` · `toxicity` · `scam` · `nsfw` (`nsfw` is the only category available for images)

### API keys

```http
POST /v1/apikeys
Authorization: Bearer <token>
Content-Type: application/json

{ "name": "prod", "request_limit": 1000 }

→ 201 { "id": "...", "name": "prod", "key": "sk-...", "request_limit": 1000, "created_at": "..." }
```

The raw `key` is shown once, on creation — only its hash is stored. Use it via the `X-API-Key` header instead of a JWT bearer token for programmatic access:

```http
POST /v1/moderate/text
X-API-Key: sk-...
Content-Type: application/json

{ "text": "..." }
```

`GET /v1/apikeys` lists your keys (without the raw value), `DELETE /v1/apikeys/{id}` revokes one.

### Rate limiting

Requests authenticated via `X-API-Key` are rate-limited per key against its `request_limit`, on a rolling daily window. Exceeding it returns `429 Too Many Requests`. JWT-authenticated requests (dashboard/direct login) are not rate-limited.

### Webhook payload

If `callback_url` was provided, the worker sends a POST after processing:

```json
{
  "task_id": "...",
  "status": "completed",
  "decision": "blocked",
  "scores": { "spam": 0.91 },
  "model_versions": { "spam": "0.1.0-stub" }
}
```

---

## Tests

```bash
cd backend

# Unit tests (no server required)
pytest tests/unit/

# E2E API tests (requires the full stack running —
# `docker compose up -d` from the repo root)
pytest tests/e2e/
```

E2E tests go through nginx (`http://localhost:80`, configured in [tests/config.yaml](backend/tests/config.yaml)), same as any other client of the deployed stack — `api` itself has no host port to hit directly.

54 tests total: unit tests run against fake in-memory repositories (no I/O), e2e tests run the full pipeline against a live stack via [Tavern](https://tavern.readthedocs.io/).

## Project structure

```
backend/
├── api/v1/            # HTTP layer — routers, schemas
│   ├── auth.py
│   ├── apikeys.py
│   └── moderation.py
├── api/dependencies.py    # DI wiring — auth (JWT/API key), rate limiting
├── core/               # Config, security, logging, rate limiting
├── domain/
│   ├── entities.py         # Domain dataclasses (User, ApiKey, ModerationTask)
│   └── services/            # Business logic (UserService, ApiKeyService, ModerationService)
├── infrastructure/
│   ├── db/             # SQLAlchemy models, repositories, unit of work
│   ├── redis/          # Redis client, task queue
│   ├── storage/        # S3/MinIO client
│   └── monitoring/     # Prometheus metric definitions (api / worker, separate registries)
├── ml/
│   └── inference.py    # Keyword-based moderation stubs (text + image)
├── workers/
│   ├── worker.py       # Main loop (BRPOP → process → loop)
│   └── tasks.py        # Task processor (inference + DB update + webhook)
└── tests/
    ├── unit/           # Fake-repository tests
    └── e2e/            # Tavern e2e tests
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENGINE` | `sqlite+aiosqlite:///./local.db` | SQLAlchemy database URL |
| `REDIS_HOST` | `127.0.0.1` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_DB` | `0` | Redis DB index |
| `MINIO_URL` | `http://127.0.0.1:9000` | MinIO/S3 endpoint |
| `MINIO_ROOT_USER` | `minioadmin` | MinIO access key |
| `MINIO_ROOT_PASSWORD` | `minioadmin` | MinIO secret key |
| `JWT_SECRET_KEY` | `my-secret-key` | JWT signing secret — **override in production** |
| `JWT_TOKEN_LIFETIME` | `12` | JWT expiry, hours |
| `LOG_LEVEL` | `INFO` | Logging level |

See [`backend/.env.example`](backend/.env.example) for a ready-to-copy template.

## Roadmap

- [x] Async moderation pipeline (API → Redis → worker → DB)
- [x] 4 moderation categories (spam, toxicity, scam, nsfw)
- [x] Image moderation (S3/MinIO upload + worker inference)
- [x] JWT authentication
- [x] API keys (create/list/delete, `X-API-Key` auth)
- [x] Webhook callbacks
- [x] Rate limiting (per API key, daily window, JWT unlimited)
- [x] Prometheus metrics + Grafana dashboard
- [x] nginx reverse proxy (load-balances scaled `api` replicas)
- [ ] Frontend dashboard
- [ ] Load testing (Locust)
- [ ] Model versioning — planned for once real ML models replace the stubs
