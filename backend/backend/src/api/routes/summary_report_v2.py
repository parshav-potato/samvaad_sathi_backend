"""V2 Summary Report routes with Lite response format."""
from __future__ import annotations

import logging
import fastapi
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.api.dependencies.session import get_async_session
from src.models.db.user import User
from src.models.schemas.summary_report import SummaryReportRequest
from src.models.schemas.summary_report_v2 import SummaryReportResponseLite
from src.repository.crud.interview import InterviewCRUDRepository
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.repository.crud.summary_report import SummaryReportCRUDRepository
from src.services.analysis import analysis_service
from src.services.summary_report_v2 import SummaryReportServiceV2
from src.services.analytics_events import track_analytics_event


logger = logging.getLogger(__name__)
router = fastapi.APIRouter(prefix="/v2", tags=["summary-report-v2"])


@router.post(
    "/summary-report",
    response_model=SummaryReportResponseLite,
    response_model_exclude_none=True,
    status_code=200,
    summary="Generate a V2 summary report (Lite version)",
    description=(
        "Aggregates per-question analyses into a UI-friendly summary layout with simplified feedback. "
        "Includes recommended practice, speech fluency rating with emoji, next steps, and final tip."
    ),
)
async def generate_summary_report_v2(
    payload: SummaryReportRequest,
    current_user: User = Depends(get_current_user),
    session: SQLAlchemyAsyncSession = Depends(get_async_session),
    interview_repo: InterviewCRUDRepository = Depends(get_repository(InterviewCRUDRepository)),
    qa_repo: QuestionAttemptCRUDRepository = Depends(get_repository(QuestionAttemptCRUDRepository)),
    sr_repo: SummaryReportCRUDRepository = Depends(get_repository(SummaryReportCRUDRepository)),
):
    logger.info(
        "summary_report_v2.generate.start interview_id=%s user_id=%s",
        payload.interview_id,
        current_user.id,
    )

    # Verify interview belongs to current user
    interview = await interview_repo.get_by_id_and_user(payload.interview_id, current_user.id)
    if not interview:
        logger.warning(
            "summary_report_v2.generate.denied interview_id=%s user_id=%s",
            payload.interview_id,
            current_user.id,
        )
        raise fastapi.HTTPException(status_code=404, detail="Interview not found or access denied")

    # Fetch all question attempts for interview
    attempts = await qa_repo.list_latest_reportable_by_interview(interview_id=interview.id)
    logger.debug(
        "summary_report_v2.generate.attempts_loaded interview_id=%s attempts_count=%s",
        interview.id,
        len(attempts),
    )
    analyzed_count = await analysis_service.ensure_recorded_attempts_analyzed(
        question_attempts=attempts,
        user_id=current_user.id,
        db=session,
        logger=logger,
    )
    if analyzed_count:
        attempts = await qa_repo.list_latest_reportable_by_interview(interview_id=interview.id)
        logger.info(
            "summary_report_v2.generate.pre_analysis_completed interview_id=%s analyzed_attempts=%s",
            interview.id,
            analyzed_count,
        )

    # Check if resume was used for any questions in this interview
    from src.repository.crud.interview_question import InterviewQuestionCRUDRepository
    question_repo = InterviewQuestionCRUDRepository(session)
    questions = await question_repo.list_by_interview(interview_id=interview.id)
    resume_used = any(q.resume_used for q in questions) if questions else None

    # Get candidate name from user if available
    candidate_name = getattr(current_user, "name", None)

    service = SummaryReportServiceV2(session)
    try:
        result = await service.generate_for_interview_lite(
            interview.id, attempts, interview.track, resume_used, candidate_name
        )
    except Exception:
        logger.exception(
            "summary_report_v2.generate.service_failed interview_id=%s user_id=%s",
            interview.id,
            current_user.id,
        )
        raise

    # Persist summary report (idempotent per interview)
    try:
        await sr_repo.upsert(interview_id=interview.id, report_json=result)
        await session.commit()
        logger.info(
            "summary_report_v2.generate.persisted interview_id=%s user_id=%s",
            interview.id,
            current_user.id,
        )
    except Exception:  # noqa: BLE001
        await session.rollback()
        logger.exception(
            "summary_report_v2.generate.persist_failed interview_id=%s user_id=%s",
            interview.id,
            current_user.id,
        )

    return SummaryReportResponseLite(**result)


@router.get(
    "/summary-report/{interview_id}",
    response_model=SummaryReportResponseLite,
    response_model_exclude_none=True,
    status_code=200,
    summary="Fetch a previously saved V2 summary report",
    description="Retrieves a persisted V2 Lite summary report for the interview if present.",
)
async def get_summary_report_v2(
    interview_id: int,
    current_user: User = Depends(get_current_user),
    session: SQLAlchemyAsyncSession = Depends(get_async_session),
    interview_repo: InterviewCRUDRepository = Depends(get_repository(InterviewCRUDRepository)),
    sr_repo: SummaryReportCRUDRepository = Depends(get_repository(SummaryReportCRUDRepository)),
):
    logger.info("summary_report_v2.get.start interview_id=%s user_id=%s", interview_id, current_user.id)

    interview = await interview_repo.get_by_id_and_user(interview_id, current_user.id)
    if not interview:
        logger.warning(
            "summary_report_v2.get.denied interview_id=%s user_id=%s",
            interview_id,
            current_user.id,
        )
        raise fastapi.HTTPException(status_code=404, detail="Interview not found or access denied")

    record = await sr_repo.get_by_interview_id(interview_id)
    if not record or not record.report_json:
        raise fastapi.HTTPException(status_code=404, detail="Summary report not found for this interview")

    await track_analytics_event(
        session,
        event_type="report_viewed",
        user_id=current_user.id,
        interview_id=interview.id,
        event_data={"report_type": "summary_v2", "source": "summary_report_v2.get_summary_report_v2"},
    )

    return SummaryReportResponseLite(**record.report_json)
