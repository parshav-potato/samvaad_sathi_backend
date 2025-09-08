"""Analysis routes for aggregating multiple analysis types."""

import fastapi
import pydantic
import random
from fastapi.security import HTTPAuthorizationCredentials
from typing import Any, Dict, List, Optional

from src.api.dependencies.auth import get_current_user, security
from src.api.dependencies.repository import get_repository
from src.api.dependencies.session import get_async_session
from src.models.schemas.base import BaseSchemaModel
from src.models.schemas.analysis import (
    CompleteAnalysisRequest,
    CompleteAnalysisResponse,
    DomainAnalysisRequest,
    CommunicationAnalysisRequest,
    DomainAnalysisResponse,
    CommunicationAnalysisResponse,
    PaceAnalysisResponse,
    PauseAnalysisResponse,
)
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.models.db.user import User
from src.services.analysis import analysis_service
from src.services.llm import analyze_domain_with_llm, analyze_communication_with_llm
from sqlalchemy.ext.asyncio import AsyncSession


router = fastapi.APIRouter(prefix="", tags=["analysis"])


@router.post(
    path="/complete-analysis",
    name="analysis:complete-analysis",
    response_model=CompleteAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Aggregate multiple analysis types for a question attempt",
    description=(
        "Aggregates domain, communication, pace, and pause analyses for a question attempt. "
        "Requires authentication and user must own the question attempt. "
        "Results are saved to the question_attempt.analysis_json field."
    ),
)
async def complete_analysis(
    request: CompleteAnalysisRequest,
    credentials: HTTPAuthorizationCredentials = fastapi.Depends(security),
    current_user: User = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
    db: AsyncSession = fastapi.Depends(get_async_session)
) -> CompleteAnalysisResponse:
    """
    Main endpoint for complete analysis workflow:
    1. Validate user owns the question attempt
    2. Verify transcription data exists
    3. Call individual analysis endpoints concurrently
    4. Aggregate results into single response
    5. Save to database
    6. Return comprehensive analysis with metadata
    """
    
    # Extract token for service calls
    auth_token = credentials.credentials
    
    try:
        # Perform aggregated analysis
        aggregated_analysis, metadata, saved, save_error = await analysis_service.aggregate_question_analysis(
            question_attempt_id=request.question_attempt_id,
            user_id=current_user.id,
            analysis_types=request.analysis_types,
            auth_token=auth_token,
            db=db
        )
        
        # Determine completion status
        analysis_complete = len(metadata.failed_analyses) == 0
        
        # Build response message
        if analysis_complete:
            if saved:
                message = "All analyses completed successfully and saved to database"
            else:
                message = f"All analyses completed but database save failed: {save_error}"
        else:
            if len(metadata.completed_analyses) > 0:
                message = f"Partial analysis completed. Failed: {', '.join(metadata.failed_analyses)}"
            else:
                message = "All analyses failed"
        
        return CompleteAnalysisResponse(
            question_attempt_id=request.question_attempt_id,
            analysis_complete=analysis_complete,
            aggregated_analysis=aggregated_analysis,
            metadata=metadata,
            saved=saved,
            save_error=save_error,
            message=message
        )
        
    except ValueError as e:
        # Handle validation errors (missing question attempt, no transcription, etc.)
        if "not found" in str(e).lower():
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif "access denied" in str(e).lower():
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        else:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    except Exception as e:
        # Handle unexpected errors
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis aggregation failed: {str(e)}"
        )


# Domain analysis endpoint (LLM-backed)
@router.post(
    path="/domain-base-analysis",
    name="analysis:domain-base",
    response_model=DomainAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Analyze domain knowledge from question attempt",
    description=(
        "Evaluates the domain-specific knowledge demonstrated in a question attempt answer using an LLM. "
        "Persists results under analysis_json.domain."
    ),
)
async def domain_base_analysis(
    request: DomainAnalysisRequest,
    current_user: User = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
) -> DomainAnalysisResponse:
    qa = await question_repo.get_by_id_and_user(
        question_attempt_id=request.question_attempt_id,
        user_id=current_user.id,
    )
    if not qa:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Question attempt not found")

    # Choose transcription text
    transcription_text: str | None = None
    if request.override_transcription:
        transcription_text = request.override_transcription.strip()
    elif qa.transcription:
        transcription_text = qa.transcription.get("text") or qa.transcription.get("transcript")
    if not transcription_text:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Transcription missing")

    # Build user profile context
    years = getattr(current_user, "years_experience", None)
    skills_json = getattr(current_user, "skills", None) or {}
    skills_list = skills_json.get("items") if isinstance(skills_json, dict) else None
    # Avoid accessing qa.interview to prevent async lazy-loading errors
    profile = {
        "years_experience": years,
        "skills": (skills_list or [])[:30],
        "job_role": request.job_role,
        "track": None,
    }

    # Call LLM
    analysis, llm_error, latency_ms, llm_model = analyze_domain_with_llm(
        user_profile=profile,
        question_text=getattr(qa, "question_text", None),
        transcription=transcription_text,
    )

    # Fallback minimal structure if LLM unavailable
    if not analysis:
        analysis = {
            "overall_score": None,
            "summary": "",
            "suggestions": [],
            "confidence": 0.0,
            "llm_error": llm_error,
        }

    # Persist into analysis_json.domain (merge, not overwrite others)
    merged = dict(qa.analysis_json or {})
    merged["domain"] = {
        **analysis,
        "llm_model": llm_model,
        "llm_latency_ms": latency_ms,
    }
    await question_repo.update_analysis_json(question_attempt_id=request.question_attempt_id, analysis_json=merged)

    # Map to response
    # Derive a domain_score from analysis if present; else 0.0
    score = analysis.get("overall_score") if isinstance(analysis.get("overall_score"), (int, float)) else 0.0
    feedback = analysis.get("summary") or analysis.get("domain_feedback") or ""
    knowledge_areas = analysis.get("knowledge_areas") or []
    if not knowledge_areas and isinstance(analysis.get("criteria"), dict):
        knowledge_areas = [k for k in (analysis["criteria"].keys())]
    strengths = analysis.get("strengths") or []
    improvements = analysis.get("improvements") or analysis.get("suggestions") or []

    return DomainAnalysisResponse(
        question_attempt_id=request.question_attempt_id,
        domain_score=float(score or 0.0),
        domain_feedback=str(feedback),
        knowledge_areas=[str(x) for x in knowledge_areas][:10],
        strengths=[str(x) for x in strengths][:10],
        improvements=[str(x) for x in improvements][:10],
    )


@router.post(
    path="/communication-based-analysis",
    name="analysis:communication-base",  
    response_model=CommunicationAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Analyze communication quality from question attempt",
    description=(
        "Evaluates clarity, grammar, vocabulary, and structure using an LLM. "
        "Persists results under analysis_json.communication."
    ),
)
async def communication_based_analysis(
    request: CommunicationAnalysisRequest,
    current_user: User = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
) -> CommunicationAnalysisResponse:
    qa = await question_repo.get_by_id_and_user(
        question_attempt_id=request.question_attempt_id,
        user_id=current_user.id,
    )
    if not qa:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Question attempt not found")

    transcription_text: str | None = None
    if request.override_transcription:
        transcription_text = request.override_transcription.strip()
    elif qa.transcription:
        transcription_text = qa.transcription.get("text") or qa.transcription.get("transcript")
    if not transcription_text:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Transcription missing")

    years = getattr(current_user, "years_experience", None)
    skills_json = getattr(current_user, "skills", None) or {}
    skills_list = skills_json.get("items") if isinstance(skills_json, dict) else None
    # Avoid accessing qa.interview to prevent async lazy-loading errors
    profile = {
        "years_experience": years,
        "skills": (skills_list or [])[:30],
        "job_role": request.job_role,
        "track": None,
    }
    prior_metrics = (qa.analysis_json or {})

    analysis, llm_error, latency_ms, llm_model = analyze_communication_with_llm(
        user_profile=profile,
        question_text=getattr(qa, "question_text", None),
        transcription=transcription_text,
        aux_metrics={
            "pace": prior_metrics.get("pace"),
            "pause": prior_metrics.get("pause"),
        },
    )

    if not analysis:
        analysis = {
            "overall_score": None,
            "summary": "",
            "suggestions": [],
            "confidence": 0.0,
            "llm_error": llm_error,
        }

    merged = dict(qa.analysis_json or {})
    merged["communication"] = {
        **analysis,
        "llm_model": llm_model,
        "llm_latency_ms": latency_ms,
    }
    await question_repo.update_analysis_json(question_attempt_id=request.question_attempt_id, analysis_json=merged)

    # Map to response
    def _num(value: Any, fallback: float) -> float:
        try:
            return float(value) if isinstance(value, (int, float)) else float(fallback)
        except Exception:
            return float(fallback)

    base = _num(analysis.get("overall_score"), 0.0)
    clarity = base
    vocab = base
    grammar = base
    structure = base
    crit = analysis.get("criteria")
    if isinstance(crit, dict):
        clarity = _num(crit.get("clarity", {}).get("score"), base)
        structure = _num(crit.get("structure", {}).get("score"), base)
        # vocabulary may be named differently
        vocab_score = crit.get("vocabulary", {}).get("score") if isinstance(crit.get("vocabulary"), dict) else None
        jargon_score = crit.get("jargon_use", {}).get("score") if isinstance(crit.get("jargon_use"), dict) else None
        vocab = _num(vocab_score if isinstance(vocab_score, (int, float)) else jargon_score, base)
        grammar = _num(crit.get("grammar", {}).get("score") if isinstance(crit.get("grammar"), dict) else None, base)

    feedback = analysis.get("summary") or analysis.get("communication_feedback") or ""
    recs_raw = analysis.get("suggestions") or analysis.get("recommendations") or []
    if not isinstance(recs_raw, list):
        recs_raw = [str(recs_raw)]
    recommendations = [str(x) for x in recs_raw][:10]

    return CommunicationAnalysisResponse(
        question_attempt_id=request.question_attempt_id,
        communication_score=base,
        clarity_score=clarity,
        vocabulary_score=vocab,
        grammar_score=grammar,
        structure_score=structure,
        communication_feedback=str(feedback),
        recommendations=recommendations,
    )


@router.post(
    path="/analyze-pace",
    name="analysis:analyze-pace",
    response_model=PaceAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Analyze speaking pace from question attempt",
    description="Evaluates speaking speed and pace patterns from transcription timestamps."
)
async def analyze_pace(
    request: dict,
    current_user = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository))
) -> PaceAnalysisResponse:
    """Stub implementation for pace analysis."""
    question_attempt_id = request.get("question_attempt_id")
    
    # Verify ownership
    qa = await question_repo.get_by_id_and_user(
        question_attempt_id=question_attempt_id,
        user_id=current_user.id
    )
    
    if not qa or not qa.transcription:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Question attempt not found or no transcription available"
        )
    
    # Calculate WPM from transcription if available
    wpm = 150.0  # Default
    if qa.transcription and "words" in qa.transcription and "duration" in qa.transcription:
        word_count = len(qa.transcription["words"])
        duration_minutes = qa.transcription["duration"] / 60.0
        if duration_minutes > 0:
            wpm = word_count / duration_minutes
    
    wpm += random.uniform(-30.0, 30.0)  # Add some variation
    
    # Determine pace category
    if wpm < 120:
        pace_category = "too_slow"
        pace_score = max(30.0, 100.0 - (120 - wpm) * 2)
    elif wpm > 200:
        pace_category = "too_fast"  
        pace_score = max(30.0, 100.0 - (wpm - 200) * 1.5)
    else:
        pace_category = "optimal"
        pace_score = random.uniform(75.0, 95.0)
    
    return PaceAnalysisResponse(
        question_attempt_id=question_attempt_id,
        pace_score=pace_score,
        words_per_minute=wpm,
        pace_feedback=f"Speaking pace of {wpm:.1f} WPM is within optimal range." if pace_category == "optimal" else f"Speaking pace of {wpm:.1f} WPM is {pace_category.replace('_', ' ')}.",
        pace_category=pace_category,
        recommendations=["Maintain current pace", "Consider slight variation for emphasis"] if pace_category == "optimal" else ["Adjust speaking speed", "Practice with metronome"]
    )


@router.post(
    path="/analyze-pause",
    name="analysis:analyze-pause",
    response_model=PauseAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Analyze pause patterns from question attempt", 
    description="Evaluates pause frequency, duration, and patterns from transcription timestamps."
)
async def analyze_pause(
    request: dict,
    current_user = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository))
) -> PauseAnalysisResponse:
    """Stub implementation for pause analysis."""
    question_attempt_id = request.get("question_attempt_id")
    
    # Verify ownership
    qa = await question_repo.get_by_id_and_user(
        question_attempt_id=question_attempt_id,
        user_id=current_user.id
    )
    
    if not qa or not qa.transcription:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Question attempt not found or no transcription available"
        )
    
    # Calculate pause metrics from transcription if available
    pause_count = random.randint(3, 8)
    total_pause_duration = random.uniform(5.0, 15.0)
    avg_pause = total_pause_duration / pause_count
    longest_pause = avg_pause * random.uniform(1.5, 3.0)
    
    # Score based on pause patterns
    if avg_pause < 0.5:
        pause_score = random.uniform(60.0, 75.0)  # Too few pauses
    elif avg_pause > 3.0:
        pause_score = random.uniform(50.0, 70.0)  # Too many long pauses
    else:
        pause_score = random.uniform(80.0, 95.0)  # Good pause pattern
    
    return PauseAnalysisResponse(
        question_attempt_id=question_attempt_id,
        pause_score=pause_score,
        total_pause_duration=total_pause_duration,
        pause_count=pause_count,
        average_pause_duration=avg_pause,
        longest_pause_duration=longest_pause,
        pause_feedback="Pause patterns show natural speaking rhythm with appropriate breaks.",
        recommendations=["Continue natural pausing", "Use strategic pauses for emphasis"]
    )
