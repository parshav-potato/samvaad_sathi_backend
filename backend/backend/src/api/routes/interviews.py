import fastapi

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.models.schemas.interview import InterviewCreate, InterviewInResponse, GeneratedQuestionsInResponse, InterviewsListResponse, InterviewItem, QuestionsListResponse, QuestionAttemptsListResponse, QuestionAttemptItem, GenerateQuestionsRequest, CreateAttemptResponse, InterviewQuestionOut, CompleteInterviewRequest
from src.repository.crud.interview import InterviewCRUDRepository
from src.repository.crud.interview_question import InterviewQuestionCRUDRepository
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.services.llm import generate_interview_questions_with_llm
from src.services.whisper import strip_word_level_data


router = fastapi.APIRouter(prefix="", tags=["interviews"])


@router.post(
    path="/interviews/create",
    name="interviews:create",
    response_model=InterviewInResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Create or resume an interview session",
    description=(
        "Starts a new interview session for the current user with the specified track, or resumes the active session "
        "if one already exists for that track. Accepts optional 'difficulty' (easy|medium|hard), default 'medium'."
    ),
)
async def create_or_resume_interview(
    payload: InterviewCreate,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
) -> InterviewInResponse:
    # Check if the user has an active session; if so, resume instead of creating a new one
    active = await interview_repo.get_active_by_user(user_id=current_user.id)
    if active is not None and active.track == payload.track:
        return InterviewInResponse(
            interview_id=active.id,
            track=active.track,
            difficulty=active.difficulty,
            status=active.status,
            created_at=active.created_at,
            resumed=True,
        )

    difficulty = (payload.difficulty or "medium").lower()
    if difficulty not in ("easy", "medium", "hard"):
        difficulty = "medium"
    interview = await interview_repo.create_interview(user_id=current_user.id, track=payload.track, difficulty=difficulty)
    return InterviewInResponse(
        interview_id=interview.id,
        track=interview.track,
        difficulty=interview.difficulty,
        status=interview.status,
        created_at=interview.created_at,
        resumed=False,
    )


@router.post(
    path="/interviews/generate-questions",
    name="interviews:generate-questions",
    response_model=GeneratedQuestionsInResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Generate interview questions for the active session",
    description=(
        "Generates and persists a set of questions for the current user's active interview. Uses an LLM when available, "
        "falls back to static questions otherwise. Accepts optional 'use_resume' boolean (default true) to control whether "
        "resume text is used for question generation."
    ),
)
async def generate_questions(
    payload: GenerateQuestionsRequest = GenerateQuestionsRequest(),
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
    question_repo: InterviewQuestionCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewQuestionCRUDRepository)),
) -> GeneratedQuestionsInResponse:
    # Determine target interview: explicit interview_id (if provided and belongs to user) else current active
    interview = None
    if getattr(payload, "interview_id", None) is not None:
        interview = await interview_repo.get_by_id(interview_id=payload.interview_id)  # type: ignore[arg-type]
        if interview is None or interview.user_id != current_user.id:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")
        if interview.status != "active":
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="Only active interviews can generate questions")
    else:
        interview = await interview_repo.get_active_by_user(user_id=current_user.id)
        if interview is None:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="No active interview to generate questions for")

    # Generate questions (stateless - no caching for ECS compatibility)
    cached = False
    
    # Use resume context if present on user and use_resume is True
    resume_context = getattr(current_user, "resume_text", None) if payload.use_resume else None
    questions, llm_error, latency_ms, llm_model, items = await generate_interview_questions_with_llm(
        track=interview.track,
        context_text=resume_context,
        count=5,
        difficulty=interview.difficulty,
    )
    if not questions:
        questions = [
            f"Describe your recent project in {interview.track}.",
            f"What core concepts are essential in {interview.track}?",
            f"Explain a challenging problem you solved in {interview.track} and how.",
            f"How do you evaluate models in {interview.track}?",
            f"Discuss trade-offs between common methods in {interview.track}.",
        ]
    qs = {
        "questions": questions,
        "llm_error": llm_error,
        "latency_ms": latency_ms,
        "llm_model": llm_model,
        "items": items,
    }

    # Persist question records only if they don't exist yet for this interview (idempotent-ish)
    existing = await question_repo.list_by_interview(interview_id=interview.id)
    persisted = existing
    if not existing:
        # Convert questions and items to the format expected by create_batch
        questions_data = []
        if items:  # If we have structured data from LLM
            for item in items:
                questions_data.append({
                    "text": item.get("text", ""),
                    "topic": item.get("topic")
                })
        else:  # Fallback to plain question strings
            for question in questions:
                questions_data.append({
                    "text": question,
                    "topic": None
                })
        
        persisted = await question_repo.create_batch(
            interview_id=interview.id,
            questions_data=questions_data
        )

    return GeneratedQuestionsInResponse(
        interview_id=interview.id,
        track=interview.track,
        count=len(persisted),
        questions=[q.text for q in persisted],
        items=qs.get("items"),
        cached=cached,
        llm_model=qs.get("llm_model"),  # type: ignore[union-attr]
        llm_latency_ms=qs.get("latency_ms"),  # type: ignore[union-attr]
        llm_error=qs.get("llm_error"),  # type: ignore[union-attr]
    )


@router.post(
    path="/interviews/complete",
    name="interviews:complete",
    status_code=fastapi.status.HTTP_200_OK,
    summary="Complete an interview session by id",
    description="Marks the specified interview as completed if it belongs to the current user.",
)
async def complete_interview(
    payload: CompleteInterviewRequest,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
):
    interview = await interview_repo.get_by_id(interview_id=payload.interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")
    if interview.status == "completed":
        return {
            "id": interview.id,
            "status": interview.status,
            "message": "Interview already completed",
        }
    if interview.status != "active":
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail="Only active interviews can be completed")
    updated = await interview_repo.mark_completed(interview_id=interview.id)
    return {
        "id": updated.id if updated else None,
        "status": updated.status if updated else None,
        "message": "Interview marked as completed" if updated else "No update performed",
    }


@router.get(
    path="/interviews",
    name="interviews:list",
    response_model=InterviewsListResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="List my interviews (cursor-based)",
    description=(
        "Returns the user's interviews in reverse chronological order using id-based cursor pagination. "
        "Use the returned next_cursor to fetch the next page."
    ),
)
async def list_my_interviews(
    limit: int = 20,
    cursor: int | None = None,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
) -> InterviewsListResponse:
    safe_limit = max(1, min(100, int(limit)))
    rows, next_cursor = await interview_repo.list_by_user_cursor(user_id=current_user.id, limit=safe_limit, cursor_id=cursor)
    return InterviewsListResponse(
        items=[InterviewItem(interview_id=r.id, track=r.track, difficulty=r.difficulty, status=r.status, created_at=r.created_at) for r in rows],
        next_cursor=next_cursor,
        limit=safe_limit,
    )


@router.get(
    path="/interviews/{interview_id}/questions",
    name="interviews:list-questions",
    response_model=QuestionsListResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="List questions for an interview (cursor-based)",
    description=(
        "Returns the questions for the given interview in ascending order using id-based cursor pagination. "
        "Use the returned next_cursor to fetch the next page."
    ),
)
async def list_interview_questions(
    interview_id: int,
    limit: int = 20,
    cursor: int | None = None,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
    question_repo: InterviewQuestionCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewQuestionCRUDRepository)),
) -> QuestionsListResponse:
    interview = await interview_repo.get_by_id(interview_id=interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    safe_limit = max(1, min(100, int(limit)))
    items, next_cursor = await question_repo.list_by_interview_cursor(interview_id=interview_id, limit=safe_limit, cursor_id=cursor)
    
    return QuestionsListResponse(
        interview_id=interview_id,
        items=[
            InterviewQuestionOut(
                interview_question_id=q.id,
                text=q.text,
                topic=q.topic,
                status=q.status
            ) for q in items
        ],
        next_cursor=next_cursor,
        limit=safe_limit,
    )


@router.get(
    path="/interviews/{interview_id}/question-attempts",
    name="interviews:list-question-attempts",
    response_model=QuestionAttemptsListResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="List question attempts for an interview (cursor-based)",
    description=(
        "Returns the question attempts with IDs for the given interview in ascending order using id-based cursor pagination. "
        "Use this endpoint when you need QuestionAttempt IDs for audio transcription. "
        "Use the returned next_cursor to fetch the next page."
    ),
)
async def list_interview_question_attempts(
    interview_id: int,
    limit: int = 20,
    cursor: int | None = None,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
    question_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
) -> QuestionAttemptsListResponse:
    interview = await interview_repo.get_by_id(interview_id=interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")
    safe_limit = max(1, min(100, int(limit)))
    items, next_cursor = await question_repo.list_by_interview_cursor(interview_id=interview_id, limit=safe_limit, cursor_id=cursor)
    return QuestionAttemptsListResponse(
        interview_id=interview_id,
        items=[QuestionAttemptItem(
            question_attempt_id=q.id,
            question_text=q.question_text,
            question_id=q.question_id,
            audio_url=q.audio_url,
            transcription=strip_word_level_data(q.transcription),
            created_at=q.created_at
        ) for q in items],
        next_cursor=next_cursor,
        limit=safe_limit,
    )


@router.post(
    path="/interviews/{interview_id}/questions/{question_id}/attempts",
    name="interviews:create-question-attempt",
    response_model=CreateAttemptResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Start a question attempt",
    description=(
        "Creates a new QuestionAttempt record for the specified question. "
        "Optionally updates the question status to 'in_progress'."
    ),
)
async def create_question_attempt(
    interview_id: int,
    question_id: int,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
    question_repo: InterviewQuestionCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewQuestionCRUDRepository)),
    attempt_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
) -> CreateAttemptResponse:
    # Verify interview exists and belongs to user
    interview = await interview_repo.get_by_id(interview_id=interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")
    
    # Verify question exists and belongs to the interview
    question = await question_repo.get_by_id(question_id=question_id)
    if question is None or question.interview_id != interview_id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Question not found")
    
    # Update question status to in_progress
    await question_repo.update_status(question_id=question_id, status="in_progress")
    
    # Create the question attempt
    attempt = await attempt_repo.create_attempt(
        interview_id=interview_id,
        question_id=question_id,
        question_text=question.text
    )
    
    return CreateAttemptResponse(question_attempt_id=attempt.id)


