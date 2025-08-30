import sqlalchemy
from typing import Any

from src.models.db.question_attempt import QuestionAttempt
from src.repository.crud.base import BaseCRUDRepository


class QuestionAttemptCRUDRepository(BaseCRUDRepository):
    async def create_batch(self, *, interview_id: int, questions: list[str], metadata: dict[str, Any] | None = None) -> list[QuestionAttempt]:
        created: list[QuestionAttempt] = []
        for q in questions:
            qa = QuestionAttempt(interview_id=interview_id, question_text=str(q))
            if metadata is not None:
                qa.analysis_json = {"generation": metadata}
            self.async_session.add(qa)
            created.append(qa)
        await self.async_session.commit()
        for qa in created:
            await self.async_session.refresh(qa)
        return created

    async def list_by_interview(self, *, interview_id: int) -> list[QuestionAttempt]:
        stmt = (
            sqlalchemy.select(QuestionAttempt)
            .where(QuestionAttempt.interview_id == interview_id)
            .order_by(QuestionAttempt.id.asc())
        )
        query = await self.async_session.execute(statement=stmt)
        rows = query.scalars().all()
        return list(rows)

    async def list_by_interview_cursor(self, *, interview_id: int, limit: int, cursor_id: int | None) -> tuple[list[QuestionAttempt], int | None]:
        stmt = sqlalchemy.select(QuestionAttempt).where(QuestionAttempt.interview_id == interview_id)
        if cursor_id is not None:
            stmt = stmt.where(QuestionAttempt.id > cursor_id)  # ascending id cursor
        stmt = stmt.order_by(QuestionAttempt.id.asc()).limit(limit + 1)
        query = await self.async_session.execute(statement=stmt)
        rows = list(query.scalars().all())
        next_cursor: int | None = None
        if len(rows) > limit:
            next_cursor = rows[-1].id
            rows = rows[:limit]
        return rows, next_cursor

    async def get_by_id(self, *, question_attempt_id: int) -> QuestionAttempt | None:
        """Get a question attempt by ID"""
        stmt = sqlalchemy.select(QuestionAttempt).where(QuestionAttempt.id == question_attempt_id)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def get_by_id_and_user(self, *, question_attempt_id: int, user_id: int) -> QuestionAttempt | None:
        """Get a question attempt by ID, ensuring it belongs to the specified user"""
        stmt = (
            sqlalchemy.select(QuestionAttempt)
            .join(QuestionAttempt.interview)
            .where(
                QuestionAttempt.id == question_attempt_id,
                QuestionAttempt.interview.has(user_id=user_id)
            )
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def update_audio_transcription(
        self,
        *,
        question_attempt_id: int,
        audio_url: str,
        transcription: dict
    ) -> QuestionAttempt | None:
        """Update a question attempt with audio URL and transcription data"""
        stmt = sqlalchemy.select(QuestionAttempt).where(QuestionAttempt.id == question_attempt_id)
        query = await self.async_session.execute(statement=stmt)
        question_attempt = query.scalar_one_or_none()
        
        if question_attempt:
            question_attempt.audio_url = audio_url
            question_attempt.transcription = transcription
            await self.async_session.commit()
            await self.async_session.refresh(question_attempt)
        
        return question_attempt


