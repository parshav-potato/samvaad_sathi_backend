import fastapi

from src.api.routes.users import router as users_router
from src.api.routes.resume import router as resume_router
from src.api.routes.interviews import router as interviews_router

router = fastapi.APIRouter()

router.include_router(router=users_router)
router.include_router(router=resume_router)
router.include_router(router=interviews_router)
