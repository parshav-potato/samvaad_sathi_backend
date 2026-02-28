"""CRUD repository for speech pacing practice sessions."""

import sqlalchemy
from typing import Optional

from src.models.db.pacing_practice import PacingPracticeSession
from src.repository.crud.base import BaseCRUDRepository


class PacingPracticeSessionCRUDRepository(BaseCRUDRepository):
    """Repository for speech pacing practice CRUD operations."""

    async def create_session(
        self,
        *,
        user_id: int,
        level: int,
        prompt_text: str,
        prompt_index: int,
    ) -> PacingPracticeSession:
        """Create a new pending pacing practice session."""
        session = PacingPracticeSession(
            user_id=user_id,
            level=level,
            prompt_text=prompt_text,
            prompt_index=prompt_index,
            status="pending",
        )
        self.async_session.add(session)
        await self.async_session.commit()
        await self.async_session.refresh(session)
        return session

    async def get_by_id(self, *, session_id: int) -> Optional[PacingPracticeSession]:
        """Get a pacing practice session by ID."""
        stmt = sqlalchemy.select(PacingPracticeSession).where(
            PacingPracticeSession.id == session_id
        )
        result = await self.async_session.execute(statement=stmt)
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self,
        *,
        session_id: int,
        user_id: int,
    ) -> Optional[PacingPracticeSession]:
        """Get a pacing practice session by ID and user ID."""
        stmt = (
            sqlalchemy.select(PacingPracticeSession)
            .where(PacingPracticeSession.id == session_id)
            .where(PacingPracticeSession.user_id == user_id)
        )
        result = await self.async_session.execute(statement=stmt)
        return result.scalar_one_or_none()

    async def update_with_analysis(
        self,
        *,
        session_id: int,
        transcript: str,
        words_data: dict,
        score: int,
        wpm: float,
        pause_words_interval: float,
        analysis_result: dict,
    ) -> Optional[PacingPracticeSession]:
        """Save transcription and analysis results, mark session as completed.

        updated_at is set explicitly here (in addition to the DB-level trigger)
        so that the ORM-returned object always reflects the updated timestamp
        without needing a second round-trip to the database.
        """
        import datetime
        stmt = (
            sqlalchemy.update(PacingPracticeSession)
            .where(PacingPracticeSession.id == session_id)
            .values(
                transcript=transcript,
                words_data=words_data,
                score=score,
                wpm=wpm,
                pause_words_interval=pause_words_interval,
                analysis_result=analysis_result,
                status="completed",
                # Explicit application-level value so the RETURNING clause
                # returns the correct timestamp even before the trigger fires.
                updated_at=datetime.datetime.now(datetime.timezone.utc),
            )
            .returning(PacingPracticeSession)
        )
        result = await self.async_session.execute(statement=stmt)
        await self.async_session.commit()
        return result.scalar_one_or_none()

    async def get_best_score_by_level(
        self,
        *,
        user_id: int,
        level: int,
    ) -> Optional[int]:
        """Return the highest score a user has achieved for a given level."""
        stmt = (
            sqlalchemy.select(sqlalchemy.func.max(PacingPracticeSession.score))
            .where(PacingPracticeSession.user_id == user_id)
            .where(PacingPracticeSession.level == level)
            .where(PacingPracticeSession.status == "completed")
        )
        result = await self.async_session.execute(statement=stmt)
        return result.scalar_one_or_none()

    async def get_level_bests(self, *, user_id: int) -> dict[int, Optional[int]]:
        """Return the best score per level (1-3) for a user as a dict."""
        stmt = (
            sqlalchemy.select(
                PacingPracticeSession.level,
                sqlalchemy.func.max(PacingPracticeSession.score).label("best_score"),
            )
            .where(PacingPracticeSession.user_id == user_id)
            .where(PacingPracticeSession.status == "completed")
            .group_by(PacingPracticeSession.level)
        )
        result = await self.async_session.execute(statement=stmt)
        rows = result.all()
        bests: dict[int, Optional[int]] = {1: None, 2: None, 3: None}
        for row in rows:
            bests[row.level] = row.best_score
        return bests

    async def list_by_user(
        self,
        *,
        user_id: int,
        limit: int = 20,
    ) -> list[PacingPracticeSession]:
        """List pacing practice sessions for a user, most recent first."""
        stmt = (
            sqlalchemy.select(PacingPracticeSession)
            .where(PacingPracticeSession.user_id == user_id)
            .order_by(PacingPracticeSession.created_at.desc())
            .limit(limit)
        )
        result = await self.async_session.execute(statement=stmt)
        return list(result.scalars().all())
