# Samvaad Sathi Backend

FastAPI backend with AWS Aurora PostgreSQL (async SQLAlchemy), JWT auth, OpenAI Whisper audio transcription, and containerized local dev.

## Quick Start

1) Environment
- Create `.env` at `backend/.env` (see Environment below).

2) Database (AWS Aurora)
Configure your Aurora cluster details in `backend/.env`:
```env
POSTGRES_HOST=your-aurora-cluster.cluster-xxxxxxxxx.us-west-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-secure-password
```

For local development with Docker (optional):
```powershell
cd D:\samvaad_sathi_backend\backend
docker compose up -d db
# one-time DB create
docker exec -it db psql -U postgres -d postgres -c "CREATE DATABASE app;"
```

3) Run API (local)
```powershell
cd D:\samvaad_sathi_backend\backend\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn src.main:backend_app --reload
```
- Swagger: http://127.0.0.1:8000/docs

## Environment
Place this in `backend/.env`:
```env
ENVIRONMENT=DEV
BACKEND_SERVER_HOST=127.0.0.1
BACKEND_SERVER_PORT=8000
BACKEND_SERVER_WORKERS=1

POSTGRES_SCHEMA=postgresql
POSTGRES_HOST=your-aurora-cluster.cluster-xxxxxxxxx.us-west-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-secure-password
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
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

## Features

### 🔐 Authentication & User Management
- JWT-based authentication with Bearer tokens
- User registration and login
- Secure password hashing (bcrypt + argon2)
- Protected routes with automatic token validation

### 📄 Resume Processing  
- PDF and text resume upload and extraction
- AI-powered skills extraction using OpenAI
- Years of experience detection
- Resume metadata storage and retrieval

### 🎤 Audio Transcription Pipeline
- **OpenAI Whisper Integration**: High-quality speech-to-text transcription
- **Word-level Timestamps**: Precise timing data for each transcribed word
- **Multiple Audio Formats**: WAV, MP3, M4A, FLAC support with validation
- **Stateless Processing**: Temporary file handling, no persistent storage
- **Duration & Size Validation**: Automatic audio file validation
- **Question Attempt Linking**: Audio transcriptions linked to specific interview questions

### 🎯 Interview Management
- Interview session creation by track (data_science, ml_engineering, etc.)
- AI-generated interview questions based on user resume
- Question attempt tracking with audio transcription support
- Interview completion and status management

## API Overview
Base prefix: `/api`

### 👤 Users
- `POST /api/users`: Register user (email, password, name). Returns token.
- `POST /api/login`: Login (email, password). Returns token.
- `GET /api/me`: Current user (Authorization: Bearer <token>).

### 📄 Resume (Auth Required)
- `POST /api/extract-resume`: Upload a PDF or plain text resume (Authorization: Bearer <token>). The extracted `resume_text`, `skills`, and `years_experience` are saved to the authenticated user's profile only.
- `GET /api/me/resume`: Returns the authenticated user's own resume metadata and fields (no cross-user access).
- `GET /api/get_knowledgeset`: Returns normalized skills derived from the authenticated user's stored `resume_text`. Results are cached in-memory keyed by user and resume content hash.

### 🎯 Interviews (Auth Required)
- `POST /api/interviews/create`: Create or resume an active interview session by `track` for the current user.
- `POST /api/interviews/generate-questions`: Generate questions for the active interview (LLM-backed with fallback); persists them as QuestionAttempts.
- `POST /api/interviews/complete`: Mark the current active interview as completed.
- `GET /api/interviews?limit=20&cursor=<lastId>`: Cursor-based listing (newest first). Response: `{ items: [...], next_cursor, limit }`.
- `GET /api/interviews/{id}/questions?limit=20&cursor=<lastQuestionId>`: Cursor-based listing (oldest first). Response: `{ interview_id, items, next_cursor, limit }`.
- `GET /api/interviews/{id}/question-attempts`: Get QuestionAttempt objects with IDs for audio transcription support.

### 🎤 Audio Transcription (Auth Required)
- `POST /api/transcribe-whisper`: Upload audio file and transcribe using OpenAI Whisper
  - **Request**: `multipart/form-data` with `file` (audio), `question_attempt_id` (int), `language` (optional, default: "en")
  - **Supported Formats**: WAV, MP3, M4A, FLAC (validated with proper headers)
  - **Response**: Transcription text, word-level timestamps, duration, file metadata
  - **Processing**: Stateless temporary file handling, automatic cleanup
  - **Performance**: ~6-10 seconds for 72-second audio files

## Smoke Tests
Run comprehensive end-to-end checks:
```powershell
cd D:\samvaad_sathi_backend\backend\backend
python scripts\smoke_test.py
```

**Test Coverage:**
- **Authentication**: User registration, login, token validation, negative cases
- **Resume Processing**: PDF/text upload, extraction, skills detection, knowledgeset
- **Interview Flow**: Creation, question generation, listing with pagination
- **Audio Transcription**: 
  - Real audio file processing (Speech.mp3, 72 seconds)
  - QuestionAttempt ID validation
  - Word-level timestamp verification
  - Performance validation (~6-10 second processing time)
  - Stateless operation confirmation
- **Cross-user Security**: Ensures proper user isolation
- **Error Handling**: Invalid auth, duplicate users, missing files

**Prerequisites for Audio Tests:**
- Set `OPENAI_API_KEY` in `.env`
- Ensure `assets/Speech.mp3` exists (included in repo)

## Audio Transcription Setup

### Requirements
```env
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### Usage Example
```python
import requests

# 1. Create interview and generate questions
response = requests.post("/api/interviews/create", 
                        headers={"Authorization": "Bearer <token>"},
                        json={"track": "data_science", "difficulty": "medium"})
interview_id = response.json()["id"]

requests.post("/api/interviews/generate-questions", 
              headers={"Authorization": "Bearer <token>"},
              json={"use_resume": True})

# 2. Get question attempts with IDs
response = requests.get(f"/api/interviews/{interview_id}/question-attempts",
                       headers={"Authorization": "Bearer <token>"})
question_attempts = response.json()["items"]
qa_id = question_attempts[0]["id"]

# 3. Upload and transcribe audio
with open("interview_response.mp3", "rb") as audio_file:
    files = {"file": ("response.mp3", audio_file, "audio/mpeg")}
    data = {"question_attempt_id": qa_id, "language": "en"}
    response = requests.post("/api/transcribe-whisper",
                           headers={"Authorization": "Bearer <token>"},
                           files=files, data=data)

# Response includes transcription, word timestamps, and metadata
result = response.json()
print(f"Transcription: {result['transcription']['text']}")
print(f"Duration: {result['durationSeconds']} seconds")
```

### Audio File Support
- **Formats**: WAV (RIFF), MP3 (MPEG), M4A, FLAC
- **Validation**: Header-based format verification
- **Processing**: Stateless with automatic cleanup
- **Performance**: Optimized for real-time interview responses

## Troubleshooting
- ModuleNotFoundError: run with module path: `python -m uvicorn src.main:backend_app --reload`
- Env errors (decouple): ensure `.env` exists at `backend/backend/.env`.
- Env errors (decouple): ensure `.env` exists at `backend/.env`.
- Aurora connect errors: confirm Aurora cluster is running and `POSTGRES_*` credentials are correct.
- SSL errors: Aurora requires SSL by default; connection automatically includes `sslmode=require`.
- Port conflicts: change Adminer port in `backend/docker-compose.yaml` if 8081 is taken.

## Developer Notes
- **Async Architecture**: Async SQLAlchemy session uses `expire_on_commit` from env; `False` recommended in dev.
- **Audio Processing**: Stateless operation with temporary files, no persistent audio storage
- **Security**: JWT via `python-jose`; claims include username/email, expiry from env.
- **Database**: All ORM models imported at startup to resolve relationship strings.
- **Performance**: Audio transcription optimized with async I/O operations
- **Testing**: Comprehensive smoke tests covering all major workflows including audio pipeline

## Architecture

### Audio Pipeline
```
Audio Upload → Format Validation → Temporary Storage → OpenAI Whisper → 
Transcription + Timestamps → Database Storage → Cleanup
```

### Key Components
- **Audio Processor**: `src/services/audio_processor.py` - Handles validation, temporary files, MIME detection
- **Whisper Service**: `src/services/whisper.py` - OpenAI API integration with error handling
- **Interview Models**: QuestionAttempt objects link audio transcriptions to specific questions
- **Stateless Design**: No persistent file storage, all audio processed in memory/temp files

## Template Reference
This project started from a FastAPI template. The original template README is preserved as `backend/TEMPLATE_README.md`.

For deeper details (setup, endpoints, smoke tests), see `backend/docs/DEV_GUIDE.md`.
