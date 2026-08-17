import sqlalchemy
import logging
import time
from typing import Any

from src.models.db.question_attempt import QuestionAttempt
from src.models.db.interview_question import InterviewQuestion
from src.repository.crud.base import BaseCRUDRepository
logger = logging.getLogger(__name__)

class QuestionAttemptCRUDRepository(BaseCRUDRepository):
    async def create_attempt(self, *, interview_id: int, question_id: int, question_text: str) -> QuestionAttempt:
        db_start = time.perf_counter()

        logger.info(
          "Creating question attempt | Interview=%s | Question=%s",
          interview_id,
          question_id,
        )
        """Create a new question attempt linked to a specific question"""
        attempt = QuestionAttempt(
            interview_id=interview_id,
            question_id=question_id,
            question_text=question_text
        )
        self.async_session.add(attempt)
        await self.async_session.commit()
        await self.async_session.refresh(attempt)
        logger.info(
          "Question attempt created | Attempt=%s | Interview=%s | Question=%s | DBTime=%.2fs",
          attempt.id,
          interview_id,
          question_id,
          time.perf_counter() - db_start,
        )
        return attempt

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
        """Get the latest attempt for each question in an interview, ordered by question order.
        
        When a question has multiple attempts (reattempts), only the latest attempt
        (highest attempt id) is returned. This ensures:
        1. Questions appear in their original order (by InterviewQuestion.order)
        2. Only one attempt per question is returned (the most recent one)
        """
        # Subquery to get the max attempt id for each question
        latest_attempt_subq = (
            sqlalchemy.select(
                QuestionAttempt.question_id,
                sqlalchemy.func.max(QuestionAttempt.id).label("max_id")
            )
            .where(QuestionAttempt.interview_id == interview_id)
            .group_by(QuestionAttempt.question_id)
            .subquery()
        )
        
        # Main query: join with subquery to get only the latest attempt per question
        stmt = (
            sqlalchemy.select(QuestionAttempt)
            .join(latest_attempt_subq, QuestionAttempt.id == latest_attempt_subq.c.max_id)
            .join(InterviewQuestion, QuestionAttempt.question_id == InterviewQuestion.id)
            .where(QuestionAttempt.interview_id == interview_id)
            .order_by(InterviewQuestion.order.asc())
        )
        query = await self.async_session.execute(statement=stmt)
        rows = query.scalars().all()
        logger.debug(
           "Loaded interview attempts | Interview=%s | Count=%d",
           interview_id,
           len(rows),
        )
        return list(rows)

    async def list_by_interview_cursor(self, *, interview_id: int, limit: int, cursor_id: int | None) -> tuple[list[QuestionAttempt], int | None]:
        """Get the latest attempt for each question with cursor pagination, ordered by question order.
        
        When a question has multiple attempts (reattempts), only the latest attempt
        (highest attempt id) is returned. Cursor is based on InterviewQuestion.order for stable pagination.
        """
        # Subquery to get the max attempt id for each question
        latest_attempt_subq = (
            sqlalchemy.select(
                QuestionAttempt.question_id,
                sqlalchemy.func.max(QuestionAttempt.id).label("max_id")
            )
            .where(QuestionAttempt.interview_id == interview_id)
            .group_by(QuestionAttempt.question_id)
            .subquery()
        )
        
        # Main query: join with subquery to get only the latest attempt per question
        stmt = (
            sqlalchemy.select(QuestionAttempt)
            .join(latest_attempt_subq, QuestionAttempt.id == latest_attempt_subq.c.max_id)
            .join(InterviewQuestion, QuestionAttempt.question_id == InterviewQuestion.id)
            .where(QuestionAttempt.interview_id == interview_id)
        )
        if cursor_id is not None:
            # Use question order for cursor, not attempt id (more stable for pagination)
            cursor_order_subq = (
                sqlalchemy.select(InterviewQuestion.order)
                .join(QuestionAttempt, QuestionAttempt.question_id == InterviewQuestion.id)
                .where(QuestionAttempt.id == cursor_id)
                .scalar_subquery()
            )
            stmt = stmt.where(InterviewQuestion.order > cursor_order_subq)
        stmt = stmt.order_by(InterviewQuestion.order.asc()).limit(limit + 1)
        query = await self.async_session.execute(statement=stmt)
        rows = list(query.scalars().all())
        next_cursor: int | None = None
        if len(rows) > limit:
            next_cursor = rows[-1].id
            rows = rows[:limit]
        return rows, next_cursor

    async def get_by_id(self, *, question_attempt_id: int) -> QuestionAttempt | None:
        db_start = time.perf_counter()
        """Get a question attempt by ID"""
        stmt = sqlalchemy.select(QuestionAttempt).where(QuestionAttempt.id == question_attempt_id)
        query = await self.async_session.execute(statement=stmt)
        result = query.scalar_one_or_none()
        logger.info(
          "Fetched question attempt | Attempt=%s | Found=%s | DBTime=%.2fs",
          question_attempt_id,
          result is not None,
          time.perf_counter() - db_start,
        ) 

        return result

    async def get_by_id_and_user(self, *, question_attempt_id: int, user_id: int) -> QuestionAttempt | None:
        db_start = time.perf_counter()
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
        result = query.scalar_one_or_none()

        logger.info(
        "Verified question attempt ownership | Attempt=%s | User=%s | Found=%s | DBTime=%.2fs",
        question_attempt_id,
        user_id,
        result is not None,
        time.perf_counter() - db_start,
        )

        return result

    async def update_audio_transcription(
        self,
        *,
        question_attempt_id: int,
        audio_url: str,
        transcription: dict
    ) -> QuestionAttempt | None:
        db_start = time.perf_counter()

        logger.info(
          "Updating transcription | Attempt=%s",
          question_attempt_id,
        )
        """Update a question attempt with audio URL and transcription data"""
        stmt = sqlalchemy.select(QuestionAttempt).where(QuestionAttempt.id == question_attempt_id)
        query = await self.async_session.execute(statement=stmt)
        question_attempt = query.scalar_one_or_none()
        
        if question_attempt:
            question_attempt.audio_url = audio_url
            question_attempt.transcription = transcription
            await self.async_session.commit()
            await self.async_session.refresh(question_attempt)
            logger.info(
            "Transcription saved | Attempt=%s | Audio=%s | TranscriptChars=%d | DBTime=%.2fs",
            question_attempt_id,
            bool(audio_url),
            len(transcription.get("text", "")),
            time.perf_counter() - db_start,
            )
        else:
            logger.warning(
                "Question attempt not found while saving analysis | Attempt=%s",
                question_attempt_id,
            )
        
        return question_attempt

    async def update_analysis_json(
        self,
        *,
        question_attempt_id: int,
        analysis_json: dict
    ) -> QuestionAttempt | None:
        db_start = time.perf_counter()
        logger.info(
         "Saving analysis JSON | Attempt=%s",
         question_attempt_id,
        )
        """Update a question attempt with analysis results"""
        stmt = sqlalchemy.select(QuestionAttempt).where(QuestionAttempt.id == question_attempt_id)
        query = await self.async_session.execute(statement=stmt)
        question_attempt = query.scalar_one_or_none()
        
        if question_attempt:
            question_attempt.analysis_json = analysis_json
            await self.async_session.commit()
            await self.async_session.refresh(question_attempt)
            logger.info(
              "Analysis JSON saved | Attempt=%s | DBTime=%.2fs",
              question_attempt_id,
              time.perf_counter() - db_start,
            )
        else:
            logger.warning(
            "Question attempt not found while saving analysis JSON | Attempt=%s",
            question_attempt_id,
            )
        return question_attempt

    async def get_first_by_question_id(self, *, question_id: int) -> QuestionAttempt | None:
        """Fetch the earliest attempt for a given question (useful for metadata lookups)."""
        stmt = (
            sqlalchemy.select(QuestionAttempt)
            .where(QuestionAttempt.question_id == question_id)
            .order_by(QuestionAttempt.id.asc())
            .limit(1)
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

