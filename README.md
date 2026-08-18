# FastAPI + JWT auth skeleton

## Setup

```bash
cp .env.example .env
docker compose up -d
uv sync
uv run alembic upgrade head
uv run uvicorn baseproject.main:app --reload --loop baseproject.core.asyncio_loop:selector_event_loop
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Check `/api/v1/health`, then register, login, Authorize, and `/api/v1/auth/me`.
