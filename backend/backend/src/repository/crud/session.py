import datetime
import secrets

import sqlalchemy

from src.models.db.session import Session
from src.repository.crud.base import BaseCRUDRepository


class SessionCRUDRepository(BaseCRUDRepository):
    async def create_session(self, *, user_id: int, expiry_minutes: int = 60) -> Session:
        token = secrets.token_urlsafe(48)
        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expiry_minutes)

        new_session = Session(user_id=user_id, token=token, expiry=expiry)
        self.async_session.add(new_session)
        await self.async_session.commit()
        await self.async_session.refresh(new_session)
        return new_session

    async def get_session_by_token(self, *, token: str) -> Session | None:
        stmt = sqlalchemy.select(Session).where(Session.token == token)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar()  # type: ignore


