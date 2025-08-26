# Samvaad Sathi Backend

FastAPI backend with PostgreSQL (async SQLAlchemy), JWT auth, and containerized local dev.

## Quick Start

1) Environment
- Create `.env` at `backend/backend/.env` (see Environment below).

2) Database (Docker)
```powershell
cd D:\samvaad_sathi_backend\backend
docker compose up -d db
# one-time DB create
docker exec -it db psql -U postgres -d postgres -c "CREATE DATABASE app;"
```

3) Run API (local)
```powershell
cd D:\samvaad_sathi_backend\backend\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn src.main:backend_app --reload
```
- Swagger: http://127.0.0.1:8000/docs

## Environment
Place this in `backend/backend/.env`:
```env
ENVIRONMENT=DEV
BACKEND_SERVER_HOST=127.0.0.1
BACKEND_SERVER_PORT=8000
BACKEND_SERVER_WORKERS=1

POSTGRES_SCHEMA=postgresql
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=app
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=postgres
DB_TIMEOUT=30
DB_POOL_SIZE=5
DB_MAX_POOL_CON=5
DB_POOL_OVERFLOW=10
IS_DB_ECHO_LOG=False
IS_DB_EXPIRE_ON_COMMIT=False
IS_DB_FORCE_ROLLBACK=False

IS_ALLOWED_CREDENTIALS=True

API_TOKEN=dev-api-token
AUTH_TOKEN=dev-auth-token
JWT_TOKEN_PREFIX=Bearer
JWT_SECRET_KEY=change_this_dev_secret
JWT_SUBJECT=access
JWT_ALGORITHM=HS256
JWT_MIN=1
JWT_HOUR=60
JWT_DAY=1

HASHING_ALGORITHM_LAYER_1=bcrypt
HASHING_ALGORITHM_LAYER_2=argon2
HASHING_SALT=change_this_salt
OPENAI_API_KEY= 
OPENAI_MODEL=gpt-4o-mini
```

## API Overview
Base prefix: `/api`

- Users (New)
  - `POST /api/users`: Register user (email, password, name). Returns token.
  - `POST /api/login`: Login (email, password). Returns token.
  - `GET /api/me`: Current user (Authorization: Bearer <token>).

- Accounts (Existing)
  - `POST /api/auth/signup`, `POST /api/auth/signin`
  - `GET /api/accounts`
  - `GET /api/accounts/{id}`
  - `PATCH /api/accounts/{id}` (query params)
  - `DELETE /api/accounts?id=`

## Smoke Tests
Run quick end-to-end checks:
```powershell
D:\samvaad_sathi_backend\backend\backend\venv\Scripts\python.exe D:\samvaad_sathi_backend\backend\backend\scripts\smoke_test.py
```
Covers:
- Users: register, login, me, duplicate, wrong password, missing auth
- Accounts: signup, signin, list, get by id, patch, delete

## Resume Extraction Test (Repo-Local Asset)
We include a sample resume so tests work after cloning.

Prereqs:
- Set in `backend/backend/.env`:
```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Run the test:
```powershell
cd D:\samvaad_sathi_backend\backend\backend
.\nvenv\Scripts\python.exe scripts\test_resume_upload.py
```
This will upload `assets/sample_resume.txt` to `/api/extract-resume` using an authenticated request and print the JSON response (`validated` fields and `saved: true`).

## Troubleshooting
- ModuleNotFoundError: run with module path: `python -m uvicorn src.main:backend_app --reload`
- Env errors (decouple): ensure `.env` exists at `backend/backend/.env`.
- DB connect errors: confirm docker db is running and `POSTGRES_*` match; DB `app` exists.
- Port conflicts: change Adminer port in `backend/docker-compose.yaml` if 8081 is taken.

## Developer Notes
- Async SQLAlchemy session uses `expire_on_commit` from env; `False` recommended in dev.
- All ORM models imported at startup to resolve relationship strings.
- JWT via `python-jose`; claims include username/email, expiry from env.

## Template Reference
This project started from a FastAPI template. The original template README is preserved as `backend/TEMPLATE_README.md`.

For deeper details (setup, endpoints, smoke tests), see `backend/docs/DEV_GUIDE.md`.
