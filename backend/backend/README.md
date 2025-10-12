# Samvaad Sathi Backend

FastAPI backend with Supabase PostgreSQL (async SQLAlchemy), JWT auth, OpenAI Whisper audio transcription, and containerized local dev.

## Quick Start

1) Environment
- Create `.env` at `backend/.env` (see Environment below).

2) Database (Supabase)
Configure your Supabase database details in `backend/.env`:
```env
POSTGRES_HOST=your-project-ref.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-supabase-password
```

3) Run with Docker (recommended)
```powershell
cd D:\samvaad_sathi_backend\backend\backend
# Ensure env is set at backend/.env (OPENAI_API_KEY, POSTGRES_* for Supabase)
docker compose up -d

# View logs (service name is 'api')
docker compose logs -f api
```
- App: http://localhost:8000/docs
- Uploads are stored on host at `uploads/` (bind-mounted into the container).

4) Run smoke tests (inside container)
```powershell
cd D:\samvaad_sathi_backend\backend\backend
docker compose exec api python scripts/smoke_test.py
```

5) Run API directly (local, without Docker)
```powershell
cd D:\samvaad_sathi_backend\backend\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn src.main:backend_app --reload
```
- Swagger: http://127.0.0.1:8000/docs

## Update the Docker image
Use these steps whenever you change the Dockerfile, base image, or Python dependencies.

From the repo root:

```powershell
# Rebuild the image and pull latest base layers
docker compose -f backend/backend/docker-compose.yml build --pull

# Optional: force a clean rebuild (no cache)
# docker compose -f backend/backend/docker-compose.yml build --no-cache --pull

# Start (or restart) the service
docker compose -f backend/backend/docker-compose.yml up -d

# Health check (expect 200)
(Invoke-WebRequest -UseBasicParsing http://localhost:8000/docs).StatusCode

# Tail logs (Ctrl+C to stop)
docker compose -f backend/backend/docker-compose.yml logs -f
```

Alternatively, run inside the backend folder:

```powershell
cd D:\samvaad_sathi_backend\backend\backend
docker compose build --pull
docker compose up -d
```

## Environment
Place this in `backend/.env`:
```env
ENVIRONMENT=DEV
BACKEND_SERVER_HOST=127.0.0.1
BACKEND_SERVER_PORT=8000
BACKEND_SERVER_WORKERS=1

POSTGRES_SCHEMA=postgresql
POSTGRES_HOST=your-project-ref.supabase.co
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USERNAME=postgres
POSTGRES_PASSWORD=your-supabase-password
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

### 📊 Analysis Aggregation
- **Complete Analysis Endpoint**: Single API call aggregating multiple analysis types
- **Concurrent Processing**: Domain, communication, pace, and pause analyses run in parallel (async) with per-analysis timeouts
- **Flexible Analysis Selection**: Support for all or subset of analysis types
- **Database Persistence**: Results saved to `question_attempt.analysis_json` field
- **Performance Optimized**: Sub-second response times with direct function calls
- **Error Resilience**: Graceful handling of partial failures

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
- `POST /api/interviews/complete`: Complete a specific interview by ID. Request: `{ "interviewId": number }`.
- `GET /api/interviews?limit=20&cursor=<lastId>`: Cursor-based listing (newest first). 
  - **Response**: `{ items: [{ interviewId, track, difficulty, status, createdAt, knowledgePercentage, speechFluencyPercentage, attemptsCount, resumeUsed }], next_cursor, limit }`
  - **New**: Automatically includes `knowledgePercentage` and `speechFluencyPercentage` from latest summary report (if available)
- `GET /api/interviews-with-summary?limit=20&cursor=<lastId>`: Enhanced interview listing with summary data (newest first).
  - **Response**: `{ items: [{ interviewId, track, difficulty, status, createdAt, knowledgePercentage, speechFluencyPercentage, summaryReportAvailable, attemptsCount, topActionItems }], next_cursor, limit }`
  - **Features**: Includes top 3 action items from latest summary report, summary availability flag
  - **Performance**: Optimized single query with join to summary_reports table
- `GET /api/interviews/{id}/questions?limit=20&cursor=<lastQuestionId>`: Cursor-based listing (oldest first). Response: `{ interviewId, items, next_cursor, limit }`.
- `GET /api/interviews/{id}/question-attempts`: Get QuestionAttempt objects with IDs for audio transcription support.

### 🎤 Audio Transcription (Auth Required)
- `POST /api/transcribe-whisper`: Upload audio file and transcribe using OpenAI Whisper
  - **Request**: `multipart/form-data` with `file` (audio), `question_attempt_id` (int), `language` (optional, default: "en")
  - **Supported Formats**: WAV, MP3, M4A, FLAC (validated with proper headers)
  - **Response**: Transcription text, word-level timestamps, duration, file metadata
  - **Processing**: Stateless temporary file handling, automatic cleanup
  - **Performance**: ~6-10 seconds for 72-second audio files

### 📊 Analysis & Reports (Auth Required)
- `POST /api/complete-analysis`: Aggregate multiple analysis types for a question attempt
  - **Request**: `{ question_attempt_id: int, analysis_types: ["domain", "communication", "pace", "pause"] }`
  - **Response**: Aggregated analysis results with metadata and performance stats
  - **Features**: Concurrent processing, partial failure handling, database persistence
  - **Performance**: Sub-second response times for all 4 analysis types
- `POST /api/domain-base-analysis`: Individual domain knowledge analysis
- `POST /api/communication-based-analysis`: Individual communication quality analysis  
- `POST /api/analyze-pace`: Individual speaking pace analysis
- `POST /api/analyze-pause`: Individual pause pattern analysis
- `POST /api/summary-report`: Generate comprehensive interview summary report
  - **Request**: `{ interview_id: int }`
  - **Response**: Restructured report with:
    - `reportId`: UUID identifier
    - `candidateInfo`: Interview metadata (date, role)
    - `scoreSummary`: Numeric scores (0-25 for knowledge, 0-20 for speech) with percentages
    - `overallFeedback`: Speech fluency feedback with actionable steps
    - `questionAnalysis`: Per-question feedback (null for unattempted questions)
  - **Features**: LLM-powered synthesis, fallback to heuristic scoring, database persistence
- `GET /api/summary-report/{interview_id}`: Retrieve persisted summary report
- `GET /api/summary-reports?limit=10`: List recent summary reports with scores
- `POST /api/final-report`: Generate and persist session-level report (legacy format)

## Smoke Tests
Run comprehensive end-to-end checks:
```powershell
cd D:\samvaad_sathi_backend\backend\backend
python scripts\smoke_test.py
```

Alternatively, run from the Docker container as shown above.

## Deploying Image to AWS ECR
Push the locally built image (from Docker Compose) to AWS ECR.

Pre-reqs:
- AWS account and permissions for ECR (create-repository, ecr:BatchGetImage, ecr:PutImage)
- AWS CLI v2 installed and credentials configured (or set env vars in the session)

Using helper script:
```powershell
cd D:\samvaad_sathi_backend\backend\backend
# By default, pushes backend-api:latest to <account>.dkr.ecr.ap-south-1.amazonaws.com/samvaad-sathi:latest
powershell -ExecutionPolicy Bypass -File scripts\push_to_ecr.ps1 -Region ap-south-1 -Repository samvaad-sathi -Image backend-api:latest -Tag latest

# Optional: specify AccountId explicitly
powershell -ExecutionPolicy Bypass -File scripts\push_to_ecr.ps1 -Region ap-south-1 -Repository samvaad-sathi -Image backend-api:latest -Tag latest -AccountId 123456789012
```

Manual commands (fallback):
```powershell
# Set your region
$env:AWS_DEFAULT_REGION = "ap-south-1"

# Log in to ECR (replace with your account ID)
aws ecr get-login-password --region $env:AWS_DEFAULT_REGION | docker login --username AWS --password-stdin 123456789012.dkr.ecr.ap-south-1.amazonaws.com

# Create repo if missing
aws ecr create-repository --repository-name samvaad-sathi --image-scanning-configuration scanOnPush=true --region $env:AWS_DEFAULT_REGION

# Tag and push the image that compose built (REPOSITORY=backend-api, TAG=latest)
docker tag backend-api:latest 123456789012.dkr.ecr.ap-south-1.amazonaws.com/samvaad-sathi:latest
docker push 123456789012.dkr.ecr.ap-south-1.amazonaws.com/samvaad-sathi:latest
```

### Database Management
Check database status and manage persistence:
```powershell
# Check current status
python scripts/db_manager.py status

# Initialize database (first time setup)
python scripts/db_manager.py init

# Run pending migrations
python scripts/db_manager.py migrate

# Test persistence and concurrency
python scripts/test_db_persistence.py

# Reset database (development only - DESTRUCTIVE)
python scripts/db_manager.py reset
```

**Database Persistence**: The database is now configured for persistence across application restarts. Data will not be lost when the application is restarted, and multiple instances can safely connect to the same database.

Note: A migration adds a UNIQUE constraint on `report.interview_id` to support atomic upsert. Ensure migrations are up to date before using `/api/final-report` under concurrent load.

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
- **Analysis Aggregation**:
  - Complete analysis endpoint with all 4 types
  - Partial analysis with subset of types
  - Individual analysis endpoints (domain, communication, pace, pause)
  - Authentication and authorization validation
  - Error handling for invalid inputs and non-existent records
  - Database persistence verification
- **Cross-user Security**: Ensures proper user isolation
- **Error Handling**: Invalid auth, duplicate users, missing files

**Prerequisites for Audio Tests:**
- Set `OPENAI_API_KEY` in `.env`
- Ensure `assets/Speech.mp3` exists (included in repo)

## Troubleshooting
- ModuleNotFoundError: run with module path: `python -m uvicorn src.main:backend_app --reload`
- Env errors (decouple): ensure `.env` exists at `backend/.env`.
- Supabase connect errors: confirm Supabase project is running and `POSTGRES_*` credentials are correct.
- SSL errors: Supabase requires SSL by default; connection automatically includes `sslmode=require`.
- Port conflicts: change the port mapping (`8000:8000`) in `backend/backend/docker-compose.yml`.

## Developer Notes
- **Async Architecture**: Async SQLAlchemy session uses `expire_on_commit` from env; `False` recommended in dev.
- **Audio Processing**: Stateless operation with temporary files, no persistent audio storage
- **Security**: JWT via `python-jose`; claims include username/email, expiry from env.
- **Database**: All ORM models imported at startup to resolve relationship strings.
- **Performance**: Audio transcription optimized with async I/O operations
- **Testing**: Comprehensive smoke tests covering all major workflows including audio pipeline

### Architecture

### Audio Pipeline
```
Audio Upload → Format Validation → Temporary Storage → OpenAI Whisper → 
Transcription + Timestamps → Database Storage → Cleanup
```

### Analysis Pipeline
```
Question Attempt → Transcription Validation → Concurrent Analysis Processing →
Domain + Communication + Pace + Pause → Result Aggregation → Database Persistence
```

### Summary Report Structure (New Format)
```json
{
  "reportId": "uuid-string",
  "candidateInfo": {
    "name": "Candidate Name (optional)",
    "interviewDate": "2024-12-15T10:30:00Z",
    "roleTopic": "Frontend Development"
  },
  "scoreSummary": {
    "knowledgeCompetence": {
      "score": 18,
      "maxScore": 25,
      "average": 3.6,
      "maxAverage": 5.0,
      "percentage": 72,
      "criteria": {
        "accuracy": 4,
        "depth": 3,
        "relevance": 4,
        "examples": 3,
        "terminology": 4
      }
    },
    "speechAndStructure": {
      "score": 16,
      "maxScore": 20,
      "average": 4.0,
      "maxAverage": 5.0,
      "percentage": 80,
      "criteria": {
        "fluency": 4,
        "structure": 4,
        "pacing": 4,
        "grammar": 4
      }
    }
  },
  "overallFeedback": {
    "speechFluency": {
      "strengths": ["Clear articulation", "Good pacing"],
      "areasOfImprovement": ["Reduce filler words", "Maintain consistent structure"],
      "actionableSteps": [
        {
          "title": "Fluency Drills",
          "description": "Record responses and identify filler word patterns"
        }
      ]
    }
  },
  "questionAnalysis": [
    {
      "id": 1,
      "totalQuestions": 5,
      "type": "Technical question",
      "question": "Explain event delegation in JavaScript",
      "feedback": {
        "knowledgeRelated": {
          "strengths": ["Correct concept explanation"],
          "areasOfImprovement": ["Provide more specific examples"],
          "actionableInsights": [
            {
              "title": "Practice Examples",
              "description": "Prepare 2-3 specific code examples for similar questions"
            }
          ]
        }
      }
    },
    {
      "id": 2,
      "totalQuestions": 5,
      "type": "Technical question",
      "question": "What is the event loop?",
      "feedback": null
    }
  ]
}
```

**Key Features:**
- **Numeric Scoring**: Knowledge (0-25) and Speech (0-20) with clear max values
- **Actionable Steps**: Structured with title + description for clarity
- **Per-Question Feedback**: Includes all questions (null feedback if not attempted)
- **Speech Focus**: Overall feedback focuses only on speech/communication aspects
- **LLM-Powered**: GPT-based synthesis with fallback to heuristic scoring

### Key Components
- **Audio Processor**: `src/services/audio_processor.py` - Handles validation, temporary files, MIME detection
- **Whisper Service**: `src/services/whisper.py` - OpenAI API integration with error handling
- **Analysis Aggregation**: `src/services/analysis.py` - Concurrent analysis processing and aggregation
- **Interview Models**: QuestionAttempt objects link audio transcriptions to specific questions
- **Analysis Persistence**: Results stored in `question_attempt.analysis_json` JSONB field
- **Stateless Design**: No persistent file storage, all audio processed in memory/temp files

## Template Reference
This project started from a FastAPI template. The original template README is preserved as `backend/TEMPLATE_README.md`.

For deeper details (setup, endpoints, smoke tests), see `backend/docs/DEV_GUIDE.md`.
