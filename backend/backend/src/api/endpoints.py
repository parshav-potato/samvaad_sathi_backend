import fastapi

from src.api.routes.users import router as users_router
from src.api.routes.resume import router as resume_router
from src.api.routes.interviews import router as interviews_router
from src.api.routes.audio import router as audio_router
from src.api.routes.analysis import router as analysis_router
from src.api.routes.report import router as report_router
from src.api.routes.auth_cognito import router as cognito_router

router = fastapi.APIRouter()

# Health check endpoint for ECS/Load Balancer
@router.get("/health", status_code=200)
async def health_check():
    return {"status": "healthy", "service": "samvaad-sathi-backend"}

router.include_router(router=users_router)
router.include_router(router=resume_router)
router.include_router(router=interviews_router)
router.include_router(router=audio_router)
router.include_router(router=analysis_router)
router.include_router(router=report_router)
router.include_router(router=cognito_router)
