"""Speech Pacing Practice routes.

Endpoints
---------
GET  /pacing-practice/levels          – dashboard: all 3 levels + overall readiness
POST /pacing-practice/session         – create a new practice session (pick prompt)
POST /pacing-practice/session/{id}/submit – submit audio, get score + metrics
GET  /pacing-practice/session/{id}    – retrieve a past session result
"""

import logging

import fastapi
from fastapi import File, UploadFile

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.models.schemas.pacing_practice import (
    PacingLevelStatus,
    PacingLevelsResponse,
    PacingAnalysisMetric,
    PacingPracticeSessionCreateRequest,
    PacingPracticeSessionDetailResponse,
    PacingPracticeSessionResponse,
    PacingPracticeSubmitResponse,
)
from src.repository.crud.pacing_practice import PacingPracticeSessionCRUDRepository
from src.services.audio_processor import validate_audio_file
from src.services.pacing_practice_service import (
    LEVEL_META,
    build_pacing_metrics,
    compute_overall_readiness,
    get_level_statuses,
    get_random_prompt,
    score_label,
)
from src.services.whisper import transcribe_audio_with_whisper

router = fastapi.APIRouter(prefix="/pacing-practice", tags=["speech-pacing"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GET /pacing-practice/levels
# ---------------------------------------------------------------------------

@router.get(
    path="/levels",
    name="pacing-practice:levels",
    response_model=PacingLevelsResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Get pacing practice levels and overall readiness",
    description=(
        "Returns the status (locked / in_progress / complete) of all three speech "
        "pacing levels and the user's overall readiness score (0-100 %). "
        "Level 2 unlocks when Level 1 best score >= 90. "
        "Level 3 unlocks when Level 2 best score >= 90."
    ),
)
async def get_pacing_levels(
    current_user=fastapi.Depends(get_current_user),
    session_repo: PacingPracticeSessionCRUDRepository = fastapi.Depends(
        get_repository(repo_type=PacingPracticeSessionCRUDRepository)
    ),
) -> PacingLevelsResponse:
    level_bests = await session_repo.get_level_bests(user_id=current_user.id)
    raw_statuses = get_level_statuses(level_bests)
    overall_readiness = compute_overall_readiness(level_bests)

    levels = [
        PacingLevelStatus(
            level=s["level"],
            name=s["name"],
            description=s["description"],
            status=s["status"],
            best_score=s["best_score"],
            unlock_threshold=s["unlock_threshold"],
            unlock_message=s["unlock_message"],
        )
        for s in raw_statuses
    ]

    return PacingLevelsResponse(levels=levels, overall_readiness=overall_readiness)


# ---------------------------------------------------------------------------
# POST /pacing-practice/session
# ---------------------------------------------------------------------------

@router.post(
    path="/session",
    name="pacing-practice:create-session",
    response_model=PacingPracticeSessionResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Create a new pacing practice session",
    description=(
        "Creates a new pacing practice session for the specified level and returns a "
        "randomly selected prompt for the user to read aloud. "
        "Levels 2 and 3 must be unlocked before they can be used (see /levels)."
    ),
)
async def create_pacing_session(
    payload: PacingPracticeSessionCreateRequest,
    current_user=fastapi.Depends(get_current_user),
    session_repo: PacingPracticeSessionCRUDRepository = fastapi.Depends(
        get_repository(repo_type=PacingPracticeSessionCRUDRepository)
    ),
) -> PacingPracticeSessionResponse:
    level = payload.level

    # --- Enforce level unlock rules ---
    if level > 1:
        level_bests = await session_repo.get_level_bests(user_id=current_user.id)
        required_level = level - 1
        gating_score = level_bests.get(required_level) or 0
        if gating_score < 90:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Level {level} is locked. Complete Level {required_level} "
                    f"with a score of 90 or above to unlock it "
                    f"(current best: {gating_score})."
                ),
            )

    # --- Pick a prompt ---
    try:
        prompt_text, prompt_index = get_random_prompt(level)
    except ValueError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    # --- Persist session ---
    db_session = await session_repo.create_session(
        user_id=current_user.id,
        level=level,
        prompt_text=prompt_text,
        prompt_index=prompt_index,
    )

    return PacingPracticeSessionResponse(
        session_id=db_session.id,
        level=db_session.level,
        level_name=LEVEL_META[level]["name"],
        prompt_text=db_session.prompt_text,
        status=db_session.status,
        created_at=db_session.created_at,
    )


# ---------------------------------------------------------------------------
# POST /pacing-practice/session/{session_id}/submit
# ---------------------------------------------------------------------------

@router.post(
    path="/session/{session_id}/submit",
    name="pacing-practice:submit-session",
    response_model=PacingPracticeSubmitResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Submit audio for a pacing practice session",
    description=(
        "Accepts an audio recording (.mp3, .wav, .m4a, .flac up to 25 MB), "
        "transcribes it with Whisper, computes WPM and pause-distribution metrics, "
        "and returns a 0-100 score. Marks the session as completed."
    ),
)
async def submit_pacing_session(
    session_id: int,
    file: UploadFile = File(..., description="Audio file. Supported: .mp3, .wav, .m4a, .flac (max 25 MB)"),
    current_user=fastapi.Depends(get_current_user),
    session_repo: PacingPracticeSessionCRUDRepository = fastapi.Depends(
        get_repository(repo_type=PacingPracticeSessionCRUDRepository)
    ),
) -> PacingPracticeSubmitResponse:
    # --- Verify session ownership ---
    db_session = await session_repo.get_by_id_and_user(
        session_id=session_id,
        user_id=current_user.id,
    )
    if not db_session:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Practice session not found or access denied",
        )
    if db_session.status == "completed":
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="This session has already been submitted. Create a new session to retry.",
        )

    # --- Validate audio ---
    try:
        audio_bytes, file_metadata = await validate_audio_file(file)
    except fastapi.HTTPException:
        raise
    except Exception as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio file validation failed: {exc}",
        )

    # --- Transcribe with Whisper ---
    transcription, whisper_error, _latency, _model = await transcribe_audio_with_whisper(
        audio_bytes=audio_bytes,
        filename=file_metadata["filename"],
        language="en",
    )

    if whisper_error or not transcription:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audio transcription failed: {whisper_error or 'unknown error'}",
        )

    words: list[dict] = transcription.get("words", [])
    if not words:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transcription returned no word-level data. Please try a clearer recording.",
        )

    # --- Compute metrics ---
    metrics = build_pacing_metrics(words)

    score = metrics["score"]
    wpm = metrics["wpm"]
    pause_interval = metrics["pause_words_interval"]

    # --- Persist results ---
    analysis_result = {
        "wpm": wpm,
        "pause_words_interval": pause_interval,
        "wpm_status": metrics["wpm_status"],
        "pause_status": metrics["pause_status"],
        "pace_raw": metrics.get("pace_raw"),
    }
    await session_repo.update_with_analysis(
        session_id=session_id,
        transcript=transcription.get("text", ""),
        words_data={"words": words},
        score=score,
        wpm=wpm,
        pause_words_interval=pause_interval,
        analysis_result=analysis_result,
    )

    # --- Check if a new level is unlocked ---
    level_unlocked: int | None = None
    next_level = db_session.level + 1
    if next_level <= 3 and score >= 90:
        # Confirm this score actually unlocks the next level for the first time
        prev_best = await session_repo.get_best_score_by_level(
            user_id=current_user.id, level=db_session.level
        )
        # prev_best is the DB value *before* our update committed; if nil or < 90
        # then this is the first qualifying attempt.
        if prev_best is None or prev_best < 90:
            level_unlocked = next_level

    # --- Build response ---
    speech_speed = PacingAnalysisMetric(
        value=round(wpm, 1),
        ideal_range="120-150",
        status=metrics["wpm_status"],
        feedback=metrics["wpm_feedback"],
    )
    pause_distribution = PacingAnalysisMetric(
        value=round(pause_interval, 1),
        ideal_range="8-12 words",
        status=metrics["pause_status"],
        feedback=metrics["pause_feedback"],
    )

    return PacingPracticeSubmitResponse(
        session_id=session_id,
        level=db_session.level,
        score=score,
        score_label=score_label(score),
        speech_speed=speech_speed,
        pause_distribution=pause_distribution,
        level_unlocked=level_unlocked,
    )


# ---------------------------------------------------------------------------
# GET /pacing-practice/session/{session_id}
# ---------------------------------------------------------------------------

@router.get(
    path="/session/{session_id}",
    name="pacing-practice:get-session",
    response_model=PacingPracticeSessionDetailResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Get a specific pacing practice session",
    description="Returns the full details and analysis result of a pacing practice session.",
)
async def get_pacing_session(
    session_id: int,
    current_user=fastapi.Depends(get_current_user),
    session_repo: PacingPracticeSessionCRUDRepository = fastapi.Depends(
        get_repository(repo_type=PacingPracticeSessionCRUDRepository)
    ),
) -> PacingPracticeSessionDetailResponse:
    db_session = await session_repo.get_by_id_and_user(
        session_id=session_id,
        user_id=current_user.id,
    )
    if not db_session:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Practice session not found or access denied",
        )

    # Reconstruct metric objects from persisted analysis_result if present
    speech_speed: PacingAnalysisMetric | None = None
    pause_distribution: PacingAnalysisMetric | None = None

    if db_session.analysis_result and db_session.wpm is not None:
        ar = db_session.analysis_result
        speech_speed = PacingAnalysisMetric(
            value=round(db_session.wpm, 1),
            ideal_range="120-150",
            status=ar.get("wpm_status", ""),
            feedback="",
        )
        if db_session.pause_words_interval is not None:
            pause_distribution = PacingAnalysisMetric(
                value=round(db_session.pause_words_interval, 1),
                ideal_range="8-12 words",
                status=ar.get("pause_status", ""),
                feedback="",
            )

    return PacingPracticeSessionDetailResponse(
        session_id=db_session.id,
        level=db_session.level,
        level_name=LEVEL_META.get(db_session.level, {}).get("name", f"Level {db_session.level}"),
        prompt_text=db_session.prompt_text,
        status=db_session.status,
        transcript=db_session.transcript,
        score=db_session.score,
        speech_speed=speech_speed,
        pause_distribution=pause_distribution,
        analysis_result=db_session.analysis_result,
        created_at=db_session.created_at,
        updated_at=db_session.updated_at,
    )
