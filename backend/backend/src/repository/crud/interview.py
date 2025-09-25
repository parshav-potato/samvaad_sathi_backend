import sqlalchemy
from typing import List, Tuple, Optional

from src.models.db.interview import Interview
from src.models.db.summary_report import SummaryReport
from src.repository.crud.base import BaseCRUDRepository


class InterviewCRUDRepository(BaseCRUDRepository):
    async def get_active_by_user(self, *, user_id: int) -> Interview | None:
        stmt = (
            sqlalchemy.select(Interview)
            .where(Interview.user_id == user_id)
            .where(Interview.status == "active")
            .order_by(Interview.id.desc())
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar()  # type: ignore

    async def create_interview(self, *, user_id: int, track: str, difficulty: str = "medium") -> Interview:
        new_interview = Interview(user_id=user_id, track=track, difficulty=difficulty, status="active")
        self.async_session.add(new_interview)
        await self.async_session.commit()
        await self.async_session.refresh(new_interview)
        return new_interview

    async def mark_completed(self, *, interview_id: int) -> Interview | None:
        stmt = sqlalchemy.select(Interview).where(Interview.id == interview_id)
        query = await self.async_session.execute(statement=stmt)
        interview: Interview | None = query.scalar()  # type: ignore
        if not interview:
            return None
        interview.status = "completed"
        await self.async_session.commit()
        await self.async_session.refresh(interview)
        return interview

    async def list_by_user_cursor(self, *, user_id: int, limit: int, cursor_id: int | None) -> tuple[list[Interview], int | None]:
        stmt = sqlalchemy.select(Interview).where(Interview.user_id == user_id)
        if cursor_id is not None:
            # created_at desc + id tie-breaker would be ideal; simplify to id cursor desc
            stmt = stmt.where(Interview.id < cursor_id)
        stmt = stmt.order_by(Interview.id.desc()).limit(limit + 1)
        query = await self.async_session.execute(statement=stmt)
        rows = list(query.scalars().all())
        next_cursor: int | None = None
        if len(rows) > limit:
            next_cursor = rows[-1].id
            rows = rows[:limit]
        return rows, next_cursor

    async def get_by_id(self, *, interview_id: int) -> Interview | None:
        stmt = sqlalchemy.select(Interview).where(Interview.id == interview_id)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar()  # type: ignore

    async def get_by_id_and_user(self, interview_id: int, user_id: int) -> Interview | None:
        stmt = (
            sqlalchemy.select(Interview)
            .where(Interview.id == interview_id)
            .where(Interview.user_id == user_id)
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar()  # type: ignore

    async def list_by_user_cursor_with_summary(self, *, user_id: int, limit: int, cursor_id: int | None) -> tuple[list[Tuple[Interview, List[SummaryReport]]], int | None]:
        """
        Get user's interviews with all their associated summary reports.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of interviews to return
            cursor_id: Cursor for pagination
            
        Returns:
            Tuple of (list of (Interview, List[SummaryReport]), next_cursor)
        """
        # Build the base query for interviews
        stmt = sqlalchemy.select(Interview).where(Interview.user_id == user_id)
        if cursor_id is not None:
            stmt = stmt.where(Interview.id < cursor_id)
        stmt = stmt.order_by(Interview.id.desc()).limit(limit + 1)
        
        query = await self.async_session.execute(statement=stmt)
        interviews = list(query.scalars().all())
        
        # Determine next cursor
        next_cursor: int | None = None
        if len(interviews) > limit:
            next_cursor = interviews[-1].id
            interviews = interviews[:limit]
        
        # Get all summary reports for these interviews
        interview_ids = [interview.id for interview in interviews]
        summary_stmt = sqlalchemy.select(SummaryReport).where(SummaryReport.interview_id.in_(interview_ids)).order_by(SummaryReport.created_at.desc())
        summary_query = await self.async_session.execute(statement=summary_stmt)
        all_summary_reports = list(summary_query.scalars().all())
        
        # Group summary reports by interview_id
        summary_reports_by_interview = {}
        for sr in all_summary_reports:
            if sr.interview_id not in summary_reports_by_interview:
                summary_reports_by_interview[sr.interview_id] = []
            summary_reports_by_interview[sr.interview_id].append(sr)
        
        # Combine interviews with their summary reports (ordered by creation date desc)
        result = [(interview, summary_reports_by_interview.get(interview.id, [])) for interview in interviews]
        
        return result, next_cursor


