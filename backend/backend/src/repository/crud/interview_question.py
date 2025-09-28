import sqlalchemy
from typing import Any

from src.models.db.interview_question import InterviewQuestion
from src.repository.crud.base import BaseCRUDRepository


class InterviewQuestionCRUDRepository(BaseCRUDRepository):
    async def create_batch(self, *, interview_id: int, questions_data: list[dict[str, Any]], resume_used: bool = False) -> list[InterviewQuestion]:
        """Create multiple interview questions with order, topic, text, and resume_used flag"""
        created: list[InterviewQuestion] = []
        for i, q_data in enumerate(questions_data):
            question = InterviewQuestion(
                interview_id=interview_id,
                text=str(q_data.get("text", "")),
                topic=q_data.get("topic"),
                order=i + 1,  # 1-indexed ordering
                status="pending",
                resume_used=resume_used
            )
            self.async_session.add(question)
            created.append(question)
        
        await self.async_session.commit()
        for question in created:
            await self.async_session.refresh(question)
        return created

    async def list_by_interview(self, *, interview_id: int) -> list[InterviewQuestion]:
        """Get all questions for an interview ordered by order field"""
        stmt = (
            sqlalchemy.select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview_id)
            .order_by(InterviewQuestion.order.asc())
        )
        query = await self.async_session.execute(statement=stmt)
        rows = query.scalars().all()
        return list(rows)

    async def list_by_interview_cursor(
        self, *, interview_id: int, limit: int, cursor_id: int | None
    ) -> tuple[list[InterviewQuestion], int | None]:
        """Get questions for an interview with cursor pagination, ordered by order field"""
        stmt = sqlalchemy.select(InterviewQuestion).where(InterviewQuestion.interview_id == interview_id)
        if cursor_id is not None:
            stmt = stmt.where(InterviewQuestion.id > cursor_id)
        stmt = stmt.order_by(InterviewQuestion.order.asc(), InterviewQuestion.id.asc()).limit(limit + 1)
        
        query = await self.async_session.execute(statement=stmt)
        rows = list(query.scalars().all())
        
        next_cursor: int | None = None
        if len(rows) > limit:
            next_cursor = rows[-1].id
            rows = rows[:limit]
        return rows, next_cursor

    async def get_by_id(self, *, question_id: int) -> InterviewQuestion | None:
        """Get a question by ID"""
        stmt = sqlalchemy.select(InterviewQuestion).where(InterviewQuestion.id == question_id)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def get_by_id_and_user(self, *, question_id: int, user_id: int) -> InterviewQuestion | None:
        """Get a question by ID, ensuring it belongs to the specified user"""
        stmt = (
            sqlalchemy.select(InterviewQuestion)
            .join(InterviewQuestion.interview)
            .where(
                InterviewQuestion.id == question_id,
                InterviewQuestion.interview.has(user_id=user_id)
            )
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def update_status(self, *, question_id: int, status: str) -> InterviewQuestion | None:
        """Update the status of a question"""
        stmt = sqlalchemy.select(InterviewQuestion).where(InterviewQuestion.id == question_id)
        query = await self.async_session.execute(statement=stmt)
        question = query.scalar_one_or_none()
        
        if question:
            question.status = status
            await self.async_session.commit()
            await self.async_session.refresh(question)
        
        return question

    async def get_questions_without_attempts(self, *, interview_id: int) -> list[InterviewQuestion]:
        """Get all questions for an interview that don't have any attempts"""
        from src.models.db.question_attempt import QuestionAttempt
        
        # Subquery to get question IDs that have attempts
        attempted_question_ids = sqlalchemy.select(QuestionAttempt.question_id).where(
            QuestionAttempt.interview_id == interview_id,
            QuestionAttempt.question_id.is_not(None)
        ).distinct()
        
        # Main query to get questions without attempts
        stmt = (
            sqlalchemy.select(InterviewQuestion)
            .where(
                InterviewQuestion.interview_id == interview_id,
                InterviewQuestion.id.not_in(attempted_question_ids)
            )
            .order_by(InterviewQuestion.order.asc())
        )
        
        query = await self.async_session.execute(statement=stmt)
        rows = query.scalars().all()
        return list(rows)

    async def get_questions_with_attempts_count(self, *, interview_id: int) -> int:
        """Get count of questions that have attempts"""
        from src.models.db.question_attempt import QuestionAttempt
        
        stmt = (
            sqlalchemy.select(sqlalchemy.func.count(sqlalchemy.distinct(QuestionAttempt.question_id)))
            .where(
                QuestionAttempt.interview_id == interview_id,
                QuestionAttempt.question_id.is_not(None)
            )
        )
        
        query = await self.async_session.execute(statement=stmt)
        return query.scalar() or 0