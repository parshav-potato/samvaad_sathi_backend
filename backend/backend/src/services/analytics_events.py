from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.analytics_event import AnalyticsEvent


async def track_analytics_event(
    session: SQLAlchemyAsyncSession,
    *,
    event_type: str,
    user_id: int | None = None,
    interview_id: int | None = None,
    event_data: dict[str, Any] | None = None,
) -> None:
    try:
        session.add(
            AnalyticsEvent(
                event_type=event_type,
                user_id=user_id,
                interview_id=interview_id,
                event_data=event_data or None,
            )
        )
        await session.commit()
    except Exception:
        await session.rollback()
