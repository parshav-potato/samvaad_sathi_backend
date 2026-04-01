from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.analytics_event import AnalyticsEvent
from src.repository.database import async_db


async def track_analytics_event(
    session: SQLAlchemyAsyncSession,
    *,
    event_type: str,
    user_id: int | None = None,
    interview_id: int | None = None,
    event_data: dict[str, Any] | None = None,
) -> None:
    # Persist via an isolated session so event commits do not affect request-scoped ORM state.
    event_session = async_db.get_session()
    try:
        event_session.add(
            AnalyticsEvent(
                event_type=event_type,
                user_id=user_id,
                interview_id=interview_id,
                event_data=event_data or None,
            )
        )
        await event_session.commit()
    except Exception:
        await event_session.rollback()
    finally:
        await event_session.close()
