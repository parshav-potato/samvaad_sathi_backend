import fastapi

from src.config.manager import settings
from src.models.db.user import User
from src.repository.crud.user import UserCRUDRepository
from src.securities.authorizations.jwt import jwt_generator
from src.api.dependencies.repository import get_repository


async def get_current_user(
    authorization: str | None = fastapi.Header(default=None, alias="Authorization"),
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = authorization.split(" ", 1)[1]
    try:
        _, email = jwt_generator.retrieve_details_from_token(token=token, secret_key=settings.JWT_SECRET_KEY)
    except Exception:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await user_repo.get_user_by_email(email=email)
    return user


