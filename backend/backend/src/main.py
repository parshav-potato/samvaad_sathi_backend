import fastapi
from dotenv import load_dotenv
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.api.endpoints import router as api_endpoint_router
from src.config.events import execute_backend_server_event_handler, terminate_backend_server_event_handler
from src.config.manager import settings


def initialize_backend_application() -> fastapi.FastAPI:
    # Load environment variables from .env if present
    load_dotenv()
    app = fastapi.FastAPI(**settings.set_backend_app_attributes)  # type: ignore

    # Tags metadata for Swagger grouping
    tags_metadata = [
        {"name": "users", "description": "User registration, login, and authentication."},
        {"name": "resume", "description": "Resume upload, parsing, and profile enrichment."},
        {"name": "interviews", "description": "Interview creation, management, and question flow."},
        {"name": "audio", "description": "Audio upload and Whisper transcription."},
        {"name": "analysis", "description": "Domain/communication analysis and pacing/pauses metrics."},
        {"name": "report", "description": "Session-level final report generation and retrieval."},
    ]
    # Attach tag descriptions to OpenAPI
    app.openapi_tags = tags_metadata  # type: ignore[attr-defined]

    # Optionally refine title/description at runtime without touching env
    try:
        app.title = "Samvaad Sathi Backend API"
        if not getattr(settings, "DESCRIPTION", None):
            app.description = "APIs for AI-driven interview practice: resume parsing, question generation, audio transcription, analyses, and reports."
    except Exception:
        # Non-fatal if attributes are not available
        pass

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=settings.IS_ALLOWED_CREDENTIALS,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    app.add_event_handler(
        "startup",
        execute_backend_server_event_handler(backend_app=app),
    )
    app.add_event_handler(
        "shutdown",
        terminate_backend_server_event_handler(backend_app=app),
    )

    app.include_router(router=api_endpoint_router, prefix=settings.API_PREFIX)

    # Enable server-side sessions for OAuth state and userinfo storage
    # Uses cookie-based signed session via Starlette's SessionMiddleware
    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)

    # Add a root endpoint
    @app.get("/")
    async def root():
        return {
            "message": "Welcome to Samvaad Sathi Backend API",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": "/api/health"
        }

    return app


backend_app: fastapi.FastAPI = initialize_backend_application()

if __name__ == "__main__":
    uvicorn.run(
        app="main:backend_app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        workers=settings.SERVER_WORKERS,
        log_level=settings.LOGGING_LEVEL,
    )
