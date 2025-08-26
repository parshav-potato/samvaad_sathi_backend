import fastapi

from src.api.dependencies.repository import get_repository
from src.api.dependencies.auth import get_current_user
from src.models.schemas.user import UserCreate, UserLogin, UserInResponse, UserWithToken
from src.repository.crud.user import UserCRUDRepository
from src.repository.crud.session import SessionCRUDRepository
from src.securities.authorizations.jwt import jwt_generator
from src.utilities.exceptions.database import EntityAlreadyExists, EntityDoesNotExist
from src.utilities.exceptions.password import PasswordDoesNotMatch
from src.utilities.exceptions.http.exc_400 import http_exc_400_credentials_bad_signin_request


router = fastapi.APIRouter(prefix="", tags=["users"])


@router.post(
    path="/users",
    name="users:register",
    response_model=UserInResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
)
async def register_user(
    payload: UserCreate,
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
    session_repo: SessionCRUDRepository = fastapi.Depends(get_repository(repo_type=SessionCRUDRepository)),
) -> UserInResponse:
    try:
        user = await user_repo.create_user(email=payload.email, password=payload.password, name=payload.name)
    except EntityAlreadyExists:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    token = jwt_generator.generate_access_token_for_user(user=user)
    await session_repo.create_session(user_id=user.id)

    return UserInResponse(
        id=user.id,
        authorized_user=UserWithToken(token=token, email=user.email, name=user.name, created_at=user.created_at),
    )


@router.post(
    path="/login",
    name="users:login",
    response_model=UserInResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
)
async def login_user(
    payload: UserLogin,
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
    session_repo: SessionCRUDRepository = fastapi.Depends(get_repository(repo_type=SessionCRUDRepository)),
) -> UserInResponse:
    try:
        user = await user_repo.verify_password(email=payload.email, password=payload.password)
    except (EntityDoesNotExist, PasswordDoesNotMatch):
        raise await http_exc_400_credentials_bad_signin_request()

    token = jwt_generator.generate_access_token_for_user(user=user)
    await session_repo.create_session(user_id=user.id)

    return UserInResponse(
        id=user.id,
        authorized_user=UserWithToken(token=token, email=user.email, name=user.name, created_at=user.created_at),
    )


@router.get(
    path="/me",
    name="users:me",
    response_model=UserInResponse,
    status_code=fastapi.status.HTTP_200_OK,
)
async def get_me(current_user=fastapi.Depends(get_current_user)) -> UserInResponse:
    token = jwt_generator.generate_access_token_for_user(user=current_user)
    return UserInResponse(
        id=current_user.id,
        authorized_user=UserWithToken(
            token=token,
            email=current_user.email,
            name=current_user.name,
            created_at=current_user.created_at,
        ),
    )


