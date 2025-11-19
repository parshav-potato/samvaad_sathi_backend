import fastapi

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.repository import get_repository
from src.models.schemas.interview import (
    InterviewCreate,
    InterviewInResponse,
    GeneratedQuestionsInResponse,
    GenerateQuestionsRequest,
    QuestionItem,
)
from src.repository.crud.interview import InterviewCRUDRepository
from src.repository.crud.interview_question import InterviewQuestionCRUDRepository
from src.services.llm import generate_interview_questions_with_llm
from src.services.static_questions import get_static_questions
from src.services.syllabus_service import syllabus_service

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
) -> GeneratedQuestionsInResponse:
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
        ) for item in qs.get("items", [])],
        cached=cached,
        llm_model=qs.get("llm_model"),
        llm_latency_ms=qs.get("latency_ms"),
        llm_error=qs.get("llm_error"),
    )
