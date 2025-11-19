from __future__ import annotations

import sqlalchemy
from typing import Iterable

from src.models.db.question_supplement import QuestionSupplement
from src.repository.crud.base import BaseCRUDRepository


class QuestionSupplementCRUDRepository(BaseCRUDRepository):
    async def get_by_question_ids(self, question_ids: Iterable[int]) -> list[QuestionSupplement]:
        ids = list(set(int(qid) for qid in question_ids if qid is not None))
        if not ids:
            return []
        stmt = sqlalchemy.select(QuestionSupplement).where(QuestionSupplement.interview_question_id.in_(ids))
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    async def get_for_question(self, question_id: int) -> QuestionSupplement | None:
        stmt = sqlalchemy.select(QuestionSupplement).where(QuestionSupplement.interview_question_id == question_id)
        result = await self.async_session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_supplement(
        self,
        *,
        question_id: int,
        supplement_type: str,
        format: str | None,
        content: str,
        rationale: str | None = None,
    ) -> QuestionSupplement:
        existing = await self.get_for_question(question_id=question_id)
        if existing:
            existing.supplement_type = supplement_type
            existing.format = format
            existing.content = content
            existing.rationale = rationale
            await self.async_session.commit()
            await self.async_session.refresh(existing)
            return existing

        entity = QuestionSupplement(
            interview_question_id=question_id,
            supplement_type=supplement_type,
            format=format,
            content=content,
            rationale=rationale,
        )
        self.async_session.add(entity)
        await self.async_session.commit()
        await self.async_session.refresh(entity)
        return entity
