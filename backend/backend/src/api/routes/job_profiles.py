import fastapi
import re
from sqlalchemy.exc import SQLAlchemyError

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.models.schemas.job_profile import (
    JobProfileCreate,
    JobProfileDeleteResponse,
    JobProfileOut,
    JobProfilesListResponse,
)
from src.repository.crud.job_profile import JobProfileCRUDRepository
from src.services.analytics_events import track_analytics_event


router = fastapi.APIRouter(prefix="/v2", tags=["job-profiles-v2"])


def _normalize_job_name(job_name: str) -> str:
    collapsed = re.sub(r"\s+", " ", job_name.strip())
    return collapsed.title()


def _raise_if_missing_table(exc: SQLAlchemyError) -> None:
    msg = str(exc).lower()
    if "job_profile" in msg and ("does not exist" in msg or "undefinedtable" in msg):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job profile feature unavailable until migration 'job_profile_001' is applied",
        )


def _to_response_item(profile) -> JobProfileOut:
    return JobProfileOut(
        job_profile_id=profile.id,
        job_name=profile.job_name,
        job_description=profile.job_description,
        company_name=profile.company_name,
        experience_level=profile.experience_level,
        skills=profile.skills,
        additional_context=profile.additional_context,
        created_by=profile.created_by,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.post(
    path="/job-profiles",
    name="job-profiles-v2:create",
    response_model=JobProfileOut,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Create a shared job profile",
)
async def create_job_profile(
    payload: JobProfileCreate,
    current_user=fastapi.Depends(get_current_user),
    job_profile_repo: JobProfileCRUDRepository = fastapi.Depends(get_repository(repo_type=JobProfileCRUDRepository)),
) -> JobProfileOut:
    try:
        profile = await job_profile_repo.create(
            job_name=_normalize_job_name(payload.job_name),
            job_description=payload.job_description.strip(),
            company_name=payload.company_name.strip() if payload.company_name else None,
            experience_level=payload.experience_level.strip() if payload.experience_level else None,
            skills=payload.skills,
            additional_context=payload.additional_context.strip() if payload.additional_context else None,
            created_by=current_user.id,
        )
    except SQLAlchemyError as exc:
        _raise_if_missing_table(exc)
        raise
    await track_analytics_event(
        job_profile_repo.async_session,
        event_type="job_profile_created",
        user_id=current_user.id,
        event_data={"job_profile_id": profile.id},
    )
    return _to_response_item(profile)


@router.get(
    path="/job-profiles",
    name="job-profiles-v2:list",
    response_model=JobProfilesListResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="List shared job profiles",
)
async def list_job_profiles(
    current_user=fastapi.Depends(get_current_user),
    job_profile_repo: JobProfileCRUDRepository = fastapi.Depends(get_repository(repo_type=JobProfileCRUDRepository)),
) -> JobProfilesListResponse:
    _ = current_user
    try:
        profiles = await job_profile_repo.list_all()
    except SQLAlchemyError as exc:
        _raise_if_missing_table(exc)
        raise
    return JobProfilesListResponse(items=[_to_response_item(profile) for profile in profiles])


@router.delete(
    path="/job-profiles/{job_profile_id}",
    name="job-profiles-v2:delete",
    response_model=JobProfileDeleteResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Delete a shared job profile",
)
async def delete_job_profile(
    job_profile_id: int,
    current_user=fastapi.Depends(get_current_user),
    job_profile_repo: JobProfileCRUDRepository = fastapi.Depends(get_repository(repo_type=JobProfileCRUDRepository)),
) -> JobProfileDeleteResponse:
    try:
        deleted = await job_profile_repo.delete(job_profile_id=job_profile_id)
    except SQLAlchemyError as exc:
        _raise_if_missing_table(exc)
        raise
    if not deleted:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Job profile not found")

    await track_analytics_event(
        job_profile_repo.async_session,
        event_type="job_profile_deleted",
        user_id=current_user.id,
        event_data={"job_profile_id": job_profile_id},
    )
    return JobProfileDeleteResponse(deleted=True, job_profile_id=job_profile_id)
