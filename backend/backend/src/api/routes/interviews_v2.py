import fastapi
import logging
from sqlalchemy.exc import SQLAlchemyError

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.models.schemas.interview import (
    InterviewCreate,
    InterviewInResponse,
    GeneratedQuestionsInResponse,
    StructurePracticeQuestionsResponse,
    GenerateQuestionsRequest,
    QuestionItem,
    QuestionItemWithHint,
    QuestionSupplementOut,
    QuestionSupplementsResponse,
)
from src.repository.crud.interview import InterviewCRUDRepository
from src.repository.crud.interview_question import InterviewQuestionCRUDRepository
from src.repository.crud.question import QuestionAttemptCRUDRepository
from src.services.llm import generate_interview_questions_with_llm
from src.services.static_questions import get_static_questions
from src.services.syllabus_service import syllabus_service
from src.services.question_supplements import (
    QuestionSupplementService,
    serialize_question_supplement,
)
from src.services.structure_hints import generate_structure_hints_for_questions

logger = logging.getLogger(__name__)
FOLLOW_UP_STRATEGY = "llm_transcription_based"


router = fastapi.APIRouter(prefix="/v2", tags=["interviews-v2"])


@router.post(
    path="/interviews/create",
    name="interviews-v2:create",
    response_model=InterviewInResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Create or resume a V2 interview session",
)
async def create_or_resume_interview_v2(
    payload: InterviewCreate,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
) -> InterviewInResponse:
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
    if difficulty not in ("easy", "medium", "hard", "expert"):
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
    name="interviews-v2:generate-questions",
    response_model=GeneratedQuestionsInResponse,
    status_code=fastapi.status.HTTP_201_CREATED,
    summary="Generate 5-question adaptive interview set",
)
async def generate_questions_v2(
    payload: GenerateQuestionsRequest,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
    question_repo: InterviewQuestionCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewQuestionCRUDRepository)),
    question_attempt_repo: QuestionAttemptCRUDRepository = fastapi.Depends(get_repository(repo_type=QuestionAttemptCRUDRepository)),
) -> GeneratedQuestionsInResponse:
    supplement_service = QuestionSupplementService(async_session=question_repo.async_session)
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

    existing = await question_repo.list_by_interview(interview_id=interview.id)
    persisted = existing
    cached = bool(existing)

    if not existing:
        resume_context = getattr(current_user, "resume_text", None) if payload.use_resume else None
        years = getattr(current_user, "years_experience", None)
        skills_json = getattr(current_user, "skills", None) or {}
        skills_list = list(skills_json.get("items", []) if isinstance(skills_json, dict) else [])
        has_resume = bool(resume_context)
        has_skills = bool(skills_list)

        role = syllabus_service._role_manager.derive_role(interview.track)
        topic_bank = syllabus_service.get_topics_for_role(role=role, difficulty=interview.difficulty)
        topics = {
            "tech": topic_bank.tech,
            "tech_allied": topic_bank.tech_allied,
            "behavioral": topic_bank.behavioral,
            "archetypes": topic_bank.archetypes,
            "depth_guidelines": topic_bank.depth_guidelines,
        }
        topics["tech_allied"] = syllabus_service.extract_tech_allied_from_resume(
            resume_text=resume_context if isinstance(resume_context, str) else None,
            skills=[str(s) for s in skills_list],
            fallback_topics=topics.get("tech_allied", []),
        )
        question_ratio = syllabus_service.compute_question_ratio(
            years_experience=years,
            has_resume_text=has_resume,
            has_skills=has_skills,
        )
        ratio = {
            "tech": question_ratio.tech,
            "tech_allied": question_ratio.tech_allied,
            "behavioral": question_ratio.behavioral,
        }
        influence = {
            "target_role": role,
            "difficulty": interview.difficulty,
            "experience_years": years,
            "skills": skills_list,
            "headline": getattr(current_user, "target_position", None),
        }

        question_count = 5

        if interview.difficulty == "easy":
            static_items = get_static_questions(role=role, count=question_count, ratio=ratio)
            questions = [item["text"] for item in static_items]
            llm_error = None
            latency_ms = 0
            llm_model = "static"
            items = static_items
        else:
            questions, llm_error, latency_ms, llm_model, items = await generate_interview_questions_with_llm(
                track=interview.track,
                context_text=resume_context,
                count=question_count,
                difficulty=interview.difficulty,
                syllabus_topics=topics,
                ratio=ratio,
                influence=influence,
            )

        if not questions:
            questions = [
                f"Walk me through a complex challenge you solved in {interview.track}.",
                f"How do you evaluate success in {interview.track} projects?",
                f"Describe a time you debugged a difficult issue in {interview.track}.",
                f"Explain an architecture decision you made recently.",
                "Tell me about a situation where you had to defend a technical decision.",
            ]

        questions_data: list[dict[str, object]] = []
        if items:
            for item in items:
                questions_data.append(
                    {
                        "text": item.get("text", ""),
                        "topic": item.get("topic"),
                        "category": item.get("category"),
                    }
                )
        else:
            for question in questions:
                questions_data.append({"text": question, "topic": None, "category": None})

        eligible_indices: list[int] = []
        for idx, data in enumerate(questions_data):
            category = str(data.get("category") or "tech").lower()
            if category != "behavioral":
                eligible_indices.append(idx)
        for idx in eligible_indices[:2]:
            questions_data[idx]["follow_up_strategy"] = FOLLOW_UP_STRATEGY

        persisted = await question_repo.create_batch(
            interview_id=interview.id,
            questions_data=questions_data,
            resume_used=payload.use_resume,
        )

        supplements_map = await _get_supplement_map(
            interview_id=interview.id,
            supplement_service=supplement_service,
            ensure_generate=True,
        )
        _validate_supplements_response(items=supplements_map, source="generate-questions")
        response_items: list[dict[str, object]] = []
        for idx, question_obj in enumerate(persisted):
            structured = items[idx] if items and idx < len(items) else None
            response_items.append(
                {
                    "interviewQuestionId": question_obj.id,
                    "text": (structured or {}).get("text") or question_obj.text,
                    "topic": (structured or {}).get("topic") or question_obj.topic,
                    "difficulty": (structured or {}).get("difficulty"),
                    "category": (structured or {}).get("category") or question_obj.category,
                    "isFollowUp": question_obj.is_follow_up,
                    "parentQuestionId": question_obj.parent_question_id,
                    "followUpStrategy": question_obj.follow_up_strategy,
                    "supplement": supplements_map.get(question_obj.id),
                }
            )
        qs = {
            "questions": [q["text"] for q in questions_data],
            "llm_error": llm_error,
            "latency_ms": latency_ms,
            "llm_model": llm_model,
            "items": response_items,
        }
    else:
        # For cached/interrupted interviews, ensure follow-up questions have parent pointers
        await _backfill_follow_up_parents(
            questions=existing,
            question_repo=question_repo,
            question_attempt_repo=question_attempt_repo,
        )
        supplements_map = await _get_supplement_map(
            interview_id=interview.id,
            supplement_service=supplement_service,
            ensure_generate=True,
        )
        _validate_supplements_response(items=supplements_map, source="generate-questions-cached")
        response_items = [
            {
                "interviewQuestionId": q.id,
                "text": q.text,
                "topic": q.topic,
                "difficulty": None,
                "category": q.category,
                "isFollowUp": q.is_follow_up,
                "parentQuestionId": q.parent_question_id,
                "followUpStrategy": q.follow_up_strategy,
                "supplement": supplements_map.get(q.id),
            }
            for q in existing
        ]
        qs = {
            "questions": [q.text for q in existing],
            "llm_error": None,
            "latency_ms": None,
            "llm_model": None,
            "items": response_items,
        }

    return GeneratedQuestionsInResponse(
        interview_id=interview.id,
        track=interview.track,
        count=len(persisted),
        questions=[q.text for q in persisted],
        question_ids=[q.id for q in persisted],
        items=[QuestionItem(
            interview_question_id=item.get("interviewQuestionId"),
            text=item.get("text", ""),
            topic=item.get("topic"),
            difficulty=item.get("difficulty"),
            category=item.get("category"),
            is_follow_up=item.get("isFollowUp", False),
            parent_question_id=item.get("parentQuestionId"),
            follow_up_strategy=item.get("followUpStrategy"),
            supplement=item.get("supplement"),
        ) for item in qs.get("items", [])],
        cached=cached,
        llm_model=qs.get("llm_model"),
        llm_latency_ms=qs.get("latency_ms"),
        llm_error=qs.get("llm_error"),
    )


@router.post(
    path="/interviews/structure-practice",
    name="interviews-v2:structure-practice",
    response_model=StructurePracticeQuestionsResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Get interview questions with structure hints for practice",
)
async def get_structure_practice_questions(
    interview_id: int = fastapi.Body(..., embed=True),
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
    question_repo: InterviewQuestionCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewQuestionCRUDRepository)),
) -> StructurePracticeQuestionsResponse:
    """
    Fetch existing interview questions with AI-generated structure hints.
    Questions and supplements are fetched from DB, only hints are newly generated.
    """
    # Validate interview ownership
    interview = await interview_repo.get_by_id(interview_id=interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail="Interview not found"
        )
    
    # Get existing questions from database
    questions = await question_repo.list_by_interview(interview_id=interview.id)
    if not questions:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="No questions found for this interview. Generate questions first."
        )
    
    # Get supplements
    supplement_service = QuestionSupplementService(async_session=question_repo.async_session)
    supplements_map = await _get_supplement_map(
        interview_id=interview.id,
        supplement_service=supplement_service,
        ensure_generate=False,  # Don't generate, just fetch existing
    )
    
    # Prepare questions data for hint generation
    questions_data = [
        {
            "text": q.text,
            "topic": q.topic,
            "category": q.category,
        }
        for q in questions
    ]
    
    # Generate structure hints using LLM
    hints_map, llm_error, latency_ms, llm_model = await generate_structure_hints_for_questions(
        questions=questions_data,
        track=interview.track,
        difficulty=interview.difficulty,
    )
    
    # Build response items with hints
    items_with_hints = []
    for q in questions:
        hint = hints_map.get(q.text, "Break down your answer logically with clear examples and explain your reasoning.")
        items_with_hints.append(
            QuestionItemWithHint(
                interview_question_id=q.id,
                text=q.text,
                topic=q.topic,
                difficulty=None,
                category=q.category,
                is_follow_up=q.is_follow_up,
                parent_question_id=q.parent_question_id,
                follow_up_strategy=q.follow_up_strategy,
                supplement=supplements_map.get(q.id),
                structure_hint=hint,
            )
        )
    
    return StructurePracticeQuestionsResponse(
        interview_id=interview.id,
        track=interview.track,
        count=len(questions),
        questions=[q.text for q in questions],
        question_ids=[q.id for q in questions],
        items=items_with_hints,
        llm_model=llm_model,
        llm_latency_ms=latency_ms,
        llm_error=llm_error,
    )


@router.post(
    path="/interviews/{interview_id}/supplements",
    name="interviews-v2:generate-supplements",
    response_model=QuestionSupplementsResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Generate supplemental code/diagram snippets for interview questions",
)
async def generate_supplements_v2(
    interview_id: int,
    regenerate: bool = fastapi.Query(
        default=False,
        description="If true, overwrite existing supplements with new LLM output",
    ),
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
) -> QuestionSupplementsResponse:
    interview = await interview_repo.get_by_id(interview_id=interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")

    supplement_service = QuestionSupplementService(async_session=interview_repo.async_session)
    supplements = await supplement_service.generate_for_interview(
        interview_id=interview.id,
        regenerate=regenerate,
    )
    return QuestionSupplementsResponse(
        interview_id=interview.id,
        supplements=[serialize_question_supplement(s) for s in supplements],
    )


@router.get(
    path="/interviews/{interview_id}/supplements",
    name="interviews-v2:get-supplements",
    response_model=QuestionSupplementsResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Fetch supplemental snippets for interview questions",
)
async def get_supplements_v2(
    interview_id: int,
    current_user=fastapi.Depends(get_current_user),
    interview_repo: InterviewCRUDRepository = fastapi.Depends(get_repository(repo_type=InterviewCRUDRepository)),
) -> QuestionSupplementsResponse:
    interview = await interview_repo.get_by_id(interview_id=interview_id)
    if interview is None or interview.user_id != current_user.id:
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND, detail="Interview not found")

    supplement_service = QuestionSupplementService(async_session=interview_repo.async_session)
    supplements = await supplement_service.get_for_interview(interview_id=interview.id)
    return QuestionSupplementsResponse(
        interview_id=interview.id,
        supplements=[serialize_question_supplement(s) for s in supplements],
    )


async def _get_supplement_map(
    *,
    interview_id: int,
    supplement_service: QuestionSupplementService,
    ensure_generate: bool = False,
) -> dict[int, QuestionSupplementOut]:
    try:
        if ensure_generate:
            supplements = await supplement_service.generate_for_interview(
                interview_id=interview_id,
                regenerate=False,
            )
        else:
            supplements = await supplement_service.get_for_interview(interview_id=interview_id)
    except SQLAlchemyError as exc:
        logger.warning("Supplements unavailable for interview %s: %s", interview_id, exc)
        return {}
    return {supp.interview_question_id: serialize_question_supplement(supp) for supp in supplements}


def _validate_supplements_response(*, items: dict[int, QuestionSupplementOut], source: str) -> None:
    """Validate supplements returned from LLM before sending to clients."""
    if not items:
        return
    allowed_types = {"code", "diagram"}
    mermaid_starters = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "classDiagram")

    for qid, supp in items.items():
        stype = (supp.supplement_type or "").lower()
        fmt = (supp.format or "").lower() if supp.format else ""
        content = supp.content or ""
        if stype not in allowed_types:
            logger.warning("Invalid supplement type (%s) for question %s from %s", stype, qid, source)
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid supplement type generated",
            )
        if stype == "diagram":
            if fmt != "mermaid":
                logger.warning("Diagram supplement missing mermaid format for question %s from %s", qid, source)
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Invalid diagram supplement format",
                )
            stripped = content.strip()
            if not stripped.startswith("```mermaid"):
                if not any(stripped.startswith(prefix) for prefix in mermaid_starters):
                    logger.warning("Mermaid supplement failed syntax precheck for question %s from %s", qid, source)
                    raise fastapi.HTTPException(
                        status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Mermaid supplement failed syntax precheck",
                    )


async def _backfill_follow_up_parents(
    *,
    questions: list,
    question_repo: InterviewQuestionCRUDRepository,
    question_attempt_repo: QuestionAttemptCRUDRepository,
) -> None:
    """Ensure follow-up questions always have a parent_question_id."""
    for q in questions:
        if getattr(q, "is_follow_up", False) and not getattr(q, "parent_question_id", None):
            attempt = await question_attempt_repo.get_first_by_question_id(question_id=q.id)
            parent_id = None
            if attempt and isinstance(attempt.analysis_json, dict):
                parent_id = attempt.analysis_json.get("follow_up", {}).get("parent_question_id")
            if parent_id:
                await question_repo.set_parent_question(question_id=q.id, parent_question_id=int(parent_id))
                q.parent_question_id = int(parent_id)
