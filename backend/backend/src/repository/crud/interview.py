import sqlalchemy

from src.models.db.interview import Interview
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

    async def create_interview(self, *, user_id: int, track: str) -> Interview:
        new_interview = Interview(user_id=user_id, track=track, status="active")
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


