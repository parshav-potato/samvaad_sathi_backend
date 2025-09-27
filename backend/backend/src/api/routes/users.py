import fastapi

from src.api.dependencies.repository import get_repository
from src.api.dependencies.auth import get_current_user
from src.config.manager import settings
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
    refresh = await session_repo.create_session(user_id=user.id, expiry_minutes=settings.REFRESH_TOKEN_EXPIRY_MINUTES)

    return UserInResponse(
        user_id=user.id,
        authorized_user=UserWithToken(token=token, 
                                    refresh_token=refresh.token,
                                    email=user.email, 
                                    name=user.name, 
                                    created_at=user.created_at,
                                    is_onboarded=user.is_onboarded if hasattr(user, 'is_onboarded') else False,
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
    refresh = await session_repo.create_session(user_id=user.id, expiry_minutes=settings.REFRESH_TOKEN_EXPIRY_MINUTES)

    return UserInResponse(
        user_id=user.id,
        authorized_user=UserWithToken(token=token, 
                                    refresh_token=refresh.token,
                                    email=user.email, 
                                    name=user.name, 
                                    created_at=user.created_at,
                                    is_onboarded=user.is_onboarded if hasattr(user, 'is_onboarded') else False,
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
            refresh_token=None,
            email=current_user.email,
            name=current_user.name,
            created_at=current_user.created_at,
            is_onboarded=getattr(current_user, 'is_onboarded', False),
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
        "Allows an authenticated user to update additional profile fields such as degree, university, "
        "target position, and years of experience. Only the provided fields are updated."
    ),
)
async def update_profile(
    profile_update: UserProfileUpdate,
    current_user=fastapi.Depends(get_current_user),
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
) -> UserProfileOut:
    # Persist updates via repository
    updated = await user_repo.update_user_profile(
        user_id=current_user.id,
        degree=profile_update.degree,
        university=profile_update.university,
        target_position=profile_update.target_position,
        years_experience=profile_update.years_experience,
    )

    # Mark onboarding complete when profile endpoint is used successfully
    if hasattr(updated, 'is_onboarded') and not updated.is_onboarded:
        await user_repo.set_onboarded(user_id=updated.id, value=True)
        updated = await user_repo.get_user_by_id(user_id=updated.id)

    return UserProfileOut(
        user_id=updated.id,
        email=updated.email,
        name=updated.name,
        degree=updated.degree,
        university=updated.university,
        target_position=updated.target_position,
        years_experience=updated.years_experience,
    )


