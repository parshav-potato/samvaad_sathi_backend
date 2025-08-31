"""Analysis routes for aggregating multiple analysis types."""

import fastapi
import pydantic
import random
from fastapi.security import HTTPAuthorizationCredentials

from src.api.dependencies.auth import get_current_user, security
from src.api.dependencies.repository import get_repository
from src.api.dependencies.session import get_async_session
from src.models.schemas.base import BaseSchemaModel
from src.models.schemas.analysis import (
    CompleteAnalysisRequest, 
    CompleteAnalysisResponse,
    DomainAnalysisResponse,
    CommunicationAnalysisResponse,
    PaceAnalysisResponse,
    PauseAnalysisResponse
)
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.services.analysis import analysis_service
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
    current_user = fastapi.Depends(get_current_user),
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


# Individual analysis endpoints (stubs for now)

@router.post(
    path="/analyze-domain",
    name="analysis:analyze-domain",
    response_model=DomainAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Analyze domain knowledge from question attempt",
    description="Evaluates the domain-specific knowledge demonstrated in a question attempt answer."
)
async def analyze_domain(
    request: dict,
    current_user = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository))
) -> DomainAnalysisResponse:
    """Stub implementation for domain analysis."""
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
    
    # Mock analysis results
    return DomainAnalysisResponse(
        question_attempt_id=question_attempt_id,
        domain_score=random.uniform(60.0, 95.0),
        domain_feedback="Domain knowledge analysis shows good understanding of core concepts.",
        knowledge_areas=["Core Concepts", "Technical Implementation", "Best Practices"],
        strengths=["Clear explanations", "Accurate terminology"],
        improvements=["Could provide more specific examples", "Deeper technical details"]
    )


@router.post(
    path="/analyze-communication",
    name="analysis:analyze-communication",  
    response_model=CommunicationAnalysisResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Analyze communication quality from question attempt",
    description="Evaluates clarity, vocabulary, grammar, and structure of the answer."
)
async def analyze_communication(
    request: dict,
    current_user = fastapi.Depends(get_current_user),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository))
) -> CommunicationAnalysisResponse:
    """Stub implementation for communication analysis."""
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
    
    # Mock analysis results
    base_score = random.uniform(75.0, 95.0)
    return CommunicationAnalysisResponse(
        question_attempt_id=question_attempt_id,
        communication_score=base_score,
        clarity_score=base_score + random.uniform(-5.0, 5.0),
        vocabulary_score=base_score + random.uniform(-10.0, 5.0),
        grammar_score=base_score + random.uniform(-3.0, 3.0),
        structure_score=base_score + random.uniform(-8.0, 8.0),
        communication_feedback="Communication analysis shows clear and structured responses.",
        recommendations=["Use more varied vocabulary", "Provide clearer examples"]
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
