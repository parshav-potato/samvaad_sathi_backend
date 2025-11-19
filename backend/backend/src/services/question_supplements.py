from __future__ import annotations

import logging
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.interview import Interview
from src.models.db.interview_question import InterviewQuestion
from src.models.db.question_supplement import QuestionSupplement
from src.models.schemas.interview import QuestionSupplementOut
from src.repository.crud.interview import InterviewCRUDRepository
from src.repository.crud.interview_question import InterviewQuestionCRUDRepository
from src.repository.crud.question_supplement import QuestionSupplementCRUDRepository
from src.services.llm import LLMSupplementItem, generate_question_supplements_with_llm

logger = logging.getLogger(__name__)


class QuestionSupplementService:
    """Handles generation and retrieval of code/diagram supplements for interview questions."""

    def __init__(self, async_session: SQLAlchemyAsyncSession):
        self._async_session = async_session
        self._interview_repo = InterviewCRUDRepository(async_session=async_session)
        self._question_repo = InterviewQuestionCRUDRepository(async_session=async_session)
        self._supplement_repo = QuestionSupplementCRUDRepository(async_session=async_session)

    async def generate_for_interview(
        self,
        *,
        interview_id: int,
        regenerate: bool = False,
    ) -> list[QuestionSupplement]:
        interview = await self._interview_repo.get_by_id(interview_id=interview_id)
        if not interview:
            return []

        questions = await self._question_repo.list_by_interview(interview_id=interview_id)
        if not questions:
            return []

        supplements = await self._supplement_repo.get_by_question_ids(q.id for q in questions)
        supplement_map = {supp.interview_question_id: supp for supp in supplements}

        target_questions = questions if regenerate else [q for q in questions if q.id not in supplement_map]
        payload = self._build_llm_payload(target_questions, interview)

        if payload:
            llm_items, error, latency_ms, model = await generate_question_supplements_with_llm(payload)
            if error:
                logger.warning("Supplement LLM call failed: %s", error)
            else:
                logger.info(
                    "Supplement LLM call complete (model=%s, latency_ms=%s, items=%s)",
                    model,
                    latency_ms,
                    len(llm_items),
                )
            await self._persist_supplements(llm_items, question_lookup={q.id: q for q in questions})
            supplements = await self._supplement_repo.get_by_question_ids(q.id for q in questions)
        else:
            supplements = list(supplement_map.values())

        # Ensure deterministic ordering
        order_map = {q.id: q.order for q in questions}
        supplements.sort(key=lambda s: order_map.get(s.interview_question_id, s.id))
        return supplements

    async def get_for_interview(self, *, interview_id: int) -> list[QuestionSupplement]:
        questions = await self._question_repo.list_by_interview(interview_id=interview_id)
        if not questions:
            return []
        supplements = await self._supplement_repo.get_by_question_ids(q.id for q in questions)
        order_map = {q.id: q.order for q in questions}
        supplements.sort(key=lambda s: order_map.get(s.interview_question_id, s.id))
        return supplements

    def _build_llm_payload(self, questions: Iterable[InterviewQuestion], interview: Interview) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for q in questions:
            payload.append(
                {
                    "questionId": q.id,
                    "text": q.text,
                    "category": q.category or "tech",
                    "topic": q.topic,
                    "difficulty": interview.difficulty,
                }
            )
        return payload

    async def _persist_supplements(
        self,
        llm_items: list[LLMSupplementItem],
        *,
        question_lookup: dict[int, InterviewQuestion],
    ) -> None:
        if not llm_items:
            return
        for item in llm_items:
            question_id = item.questionId
            if question_id not in question_lookup:
                continue
            await self._supplement_repo.upsert_supplement(
                question_id=question_id,
                supplement_type=item.supplementType,
                format=item.format,
                content=item.content,
                rationale=item.rationale,
            )


def serialize_question_supplement(entity: QuestionSupplement) -> QuestionSupplementOut:
    return QuestionSupplementOut(
        question_id=entity.interview_question_id,
        supplement_type=entity.supplement_type,
        format=entity.format,
        content=entity.content,
        rationale=entity.rationale,
    )


__all__ = ["QuestionSupplementService", "serialize_question_supplement"]
