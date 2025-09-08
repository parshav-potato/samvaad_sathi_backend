from __future__ import annotations

import fastapi
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.api.dependencies.session import get_async_session
from src.models.db.user import User
from src.models.schemas.report import FinalReportRequest, FinalReportResponse
from src.repository.crud.interview import InterviewCRUDRepository
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.repository.crud.report import ReportCRUDRepository
from src.services.report import FinalReportService


router = fastapi.APIRouter(tags=["report"])


@router.post("/final-report", response_model=FinalReportResponse, status_code=200)
async def generate_final_report(
    payload: FinalReportRequest,
    current_user: User = Depends(get_current_user),
    session: SQLAlchemyAsyncSession = Depends(get_async_session),
    interview_repo: InterviewCRUDRepository = Depends(get_repository(InterviewCRUDRepository)),
    qa_repo: QuestionAttemptCRUDRepository = Depends(get_repository(QuestionAttemptCRUDRepository)),
    report_repo: ReportCRUDRepository = Depends(get_repository(ReportCRUDRepository)),
):
    # Verify interview belongs to current user
    interview = await interview_repo.get_by_id_and_user(payload.interview_id, current_user.id)
    if not interview:
        raise fastapi.HTTPException(status_code=404, detail="Interview not found or access denied")

    # Fetch all question attempts for interview
    attempts = await qa_repo.list_by_interview(interview_id=interview.id)

    # Generate report content
    service = FinalReportService(session)
    result = await service.generate_for_interview(interview.id, attempts)

    # Persist
    saved = True
    save_error: str | None = None
    try:
        await report_repo.upsert_report(
            interview_id=interview.id,
            summary=result["summary"],
            knowledge_competence=result["knowledge_competence"],
            speech_structure_fluency=result["speech_structure_fluency"],
            overall_score=result["overall_score"],
        )
        await session.commit()
    except Exception as exc:  # noqa: BLE001
        await session.rollback()
        saved = False
        save_error = str(exc)

    response = FinalReportResponse(
        interview_id=interview.id,
        summary=result["summary"],
        knowledge_competence=result["knowledge_competence"],
        speech_structure_fluency=result["speech_structure_fluency"],
        overall_score=result["overall_score"],
        saved=saved,
        save_error=save_error,
        message="Final report generated" if saved else "Final report generated but failed to save",
    )
    return response
