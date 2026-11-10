# auth-service

FastAPI service for register, login, logout and JWT tokens, stored in SQLite.

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | /auth/register | - | Create a user (full_name, email, password 8+ chars) |
| POST | /auth/login | - | Returns `access_token` (JWT, 60 min) |
| GET | /auth/me | Bearer | Current user |
| POST | /auth/logout | Bearer | Revokes the token |
| GET | /health | - | Health check |
| GET | /metrics | - | Prometheus metrics |
| GET | /docs | - | Swagger UI |

## Run locally

    cp .env.example .env        # then put a real key in it: openssl rand -hex 32
    docker compose up --build   # http://localhost:8000/docs

## Tests

    pip install -r requirements-dev.txt
    pytest -q

## Settings (environment variables)

| Name | Default | Notes |
| --- | --- | --- |
| SECRET_KEY | (required) | 32+ random characters; the app will not start without it |
| DB_PATH | /app/data/auth.db | SQLite file |
| TOKEN_EXPIRE_MINUTES | 60 | Token lifetime |
| CORS_ORIGINS | http://localhost:4200 | Comma-separated; not needed behind the frontend's nginx proxy |
| OTEL_* | exporters off | Point at Tempo/Loki to send traces and logs |

CI/CD: the Jenkinsfile tests, builds, pushes to Azure Container Registry and updates the `auth-service` Container App.
