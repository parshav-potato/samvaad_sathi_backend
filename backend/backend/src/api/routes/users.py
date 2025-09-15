import fastapi

from src.api.dependencies.repository import get_repository
from src.api.dependencies.auth import get_current_user
from src.models.schemas.user import (
    UserCreate,
    UserLogin,
    UserInResponse,
    UserWithToken,
    UserProfileUpdate,
    UserProfileOut,
)
from src.repository.crud.user import UserCRUDRepository
from src.repository.crud.session import SessionCRUDRepository
from src.securities.authorizations.jwt import jwt_generator
from src.utilities.exceptions.database import EntityAlreadyExists, EntityDoesNotExist
from src.utilities.exceptions.password import PasswordDoesNotMatch
from src.utilities.exceptions.http.exc_400 import http_exc_400_credentials_bad_signin_request

from src.models.db.user import TargetPositionEnum


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
        user_id=user.id,
        authorized_user=UserWithToken(token=token, 
                                    email=user.email, 
                                    name=user.name, 
                                    created_at=user.created_at,
                                    degree=None,
                                    university=None,
                                    target_position=None,
                                    years_experience=None,
                                    company=None),
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
        user_id=user.id,
        authorized_user=UserWithToken(token=token, 
                                    email=user.email, 
                                    name=user.name, 
                                    created_at=user.created_at,
                                    degree=None,
                                    university=None,
                                    target_position=None,
                                    years_experience=None,
                                    company=None),
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
        user_id=current_user.id,
        authorized_user=UserWithToken(
            token=token,
            email=current_user.email,
            name=current_user.name,
            created_at=current_user.created_at,
            degree=current_user.degree,
            university=current_user.university,
            target_position=current_user.target_position,
            years_experience=current_user.years_experience,
            company=current_user.company,
        ),
    )

@router.put(
    path="/users/profile",
    name="users:update-profile",
    response_model=UserProfileOut,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Update authenticated user's profile fields",
    description=(
        "Allows an authenticated user to update additional profile fields such as degree, university, company, "
        "target position, years of experience, and profile picture. Only the provided fields are updated."
    ),
)
async def update_profile(
    # Optional scalar fields submitted as form fields so that file upload can coexist
    degree: str | None = fastapi.Form(default=None),
    university: str | None = fastapi.Form(default=None, alias="university"),
    company: str | None = fastapi.Form(default=None),
    target_position: TargetPositionEnum | None = fastapi.Form(default=None),
    years_experience: float | None = fastapi.Form(default=None),
    # Profile picture file (optional)
    profile_picture: fastapi.UploadFile | None = fastapi.File(default=None),
    current_user=fastapi.Depends(get_current_user),
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
) -> UserProfileOut:
    # Read bytes if a new profile picture is uploaded
    picture_bytes: bytes | None = None
    if profile_picture is not None:
        max_bytes = 5 * 1024 * 1024  # 5 MB guard
        content = await profile_picture.read()
        if len(content) > max_bytes:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Profile picture exceeds 5 MB limit",
            )
        picture_bytes = content

    # Persist updates via repository
    updated = await user_repo.update_user_profile(
        user_id=current_user.id,
        degree=degree,
        university=university,
        profile_picture=None,
        target_position=target_position,
        years_experience=years_experience,
        company=company,
    )

    return UserProfileOut(
        user_id=updated.id,
        email=updated.email,
        name=updated.name,
        degree=updated.degree,
        university=updated.university,
        target_position=updated.target_position,
        years_experience=updated.years_experience,
        company=updated.company,
    )


