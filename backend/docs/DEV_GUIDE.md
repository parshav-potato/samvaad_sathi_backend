# Development Guide

## Recent Additions (Auth + Sessions)
- User JWT authentication endpoints added:
  - `POST /api/users` (register)
  - `POST /api/login` (login)
  - `GET /api/me` (requires `Authorization: Bearer <token>`)
- Session persistence implemented via `Session` model and `SessionCRUDRepository`.
- Existing Account auth retained:
  - `POST /api/auth/signup`, `POST /api/auth/signin`
  - Accounts listing and management under `/api/accounts`
- JWT generator extended to support `User` tokens (`generate_access_token_for_user`).
- Async SQLAlchemy session configured to avoid `MissingGreenlet` by controlling `expire_on_commit`.
- ORM models imported at startup so relationship references (e.g., `Interview`) resolve correctly.
- Added `scripts/smoke_test.py` to quickly validate endpoints locally.

## Environment Configuration
The app reads env vars from `.env` at:
- `backend/backend/.env`

Suggested development values:
```env
# App
ENVIRONMENT=DEV
BACKEND_SERVER_HOST=127.0.0.1
BACKEND_SERVER_PORT=8000
BACKEND_SERVER_WORKERS=1

# DB (use 5433 if running the provided docker compose; otherwise 5432)
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

# CORS
IS_ALLOWED_CREDENTIALS=True

# Auth/JWT
API_TOKEN=dev-api-token
AUTH_TOKEN=dev-auth-token
JWT_TOKEN_PREFIX=Bearer
JWT_SECRET_KEY=change_this_dev_secret
JWT_SUBJECT=access
JWT_ALGORITHM=HS256
# Access token expiry minutes = JWT_MIN * JWT_HOUR * JWT_DAY
JWT_MIN=1
JWT_HOUR=60
JWT_DAY=1

# Hashing (passlib)
HASHING_ALGORITHM_LAYER_1=bcrypt
HASHING_ALGORITHM_LAYER_2=argon2
HASHING_SALT=change_this_salt
```

## Local Development (Windows PowerShell)
1) Start Postgres via docker compose (inside `backend/`):
```powershell
cd D:\samvaad_sathi_backend\backend
docker compose up -d db
```
Optionally start Adminer (DB UI). If 8081 is busy, change its port in `backend/docker-compose.yaml`:
```powershell
docker compose up -d db_editor
```

2) Create database once:
```powershell
docker exec -it db psql -U postgres -d postgres -c "CREATE DATABASE app;"
```

3) Run the API (inside `backend/backend/`):
```powershell
cd D:\samvaad_sathi_backend\backend\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn src.main:backend_app --reload
```
Swagger UI: http://127.0.0.1:8000/docs

## API Reference (Summary)
- Users
  - `POST /api/users` – Register new user (email, password, name). Returns token.
  - `POST /api/login` – Login (email, password). Returns token.
  - `GET /api/me` – Current user info (requires `Authorization: Bearer <token>`)

- Accounts (legacy module retained)
  - `POST /api/auth/signup` – Account signup
  - `POST /api/auth/signin` – Account signin
  - `GET /api/accounts` – List accounts
  - `GET /api/accounts/{id}` – Get account by ID
  - `PATCH /api/accounts/{id}` – Update account (query params)
  - `DELETE /api/accounts?id=` – Delete account by ID

## Smoke Tests
A quick local check is available at `backend/backend/scripts/smoke_test.py`.

Run it:
```powershell
D:\samvaad_sathi_backend\backend\backend\venv\Scripts\python.exe D:\samvaad_sathi_backend\backend\backend\scripts\smoke_test.py
```
It exercises:
- Users: register, login, me, duplicate, wrong password, missing auth
- Accounts: signup, signin, list, get by id, patch, delete

## Implementation Notes
- Async DB session is created with `expire_on_commit` configurable via `.env` (`IS_DB_EXPIRE_ON_COMMIT`). Setting this to `False` in dev avoids attribute refresh that can trigger `MissingGreenlet`.
- All ORM models are imported during startup so SQLAlchemy can resolve relationship strings like `Interview`.
- JWT tokens use `python-jose` and are validated with the configured `JWT_SECRET_KEY` and `JWT_ALGORITHM`.
