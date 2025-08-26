import sqlalchemy

from src.models.db.user import User
from src.repository.crud.base import BaseCRUDRepository
from src.securities.hashing.password import pwd_generator
from src.utilities.exceptions.database import EntityAlreadyExists, EntityDoesNotExist
from src.utilities.exceptions.password import PasswordDoesNotMatch


class UserCRUDRepository(BaseCRUDRepository):
    async def create_user(self, *, email: str, password: str, name: str) -> User:
        stmt = sqlalchemy.select(User).where(User.email == email)
        query = await self.async_session.execute(statement=stmt)
        if query.scalar():
            raise EntityAlreadyExists("User with this email already exists!")

        new_user = User(email=email, name=name, password_hash="")
        # Use a stable empty salt for User since the model does not store per-user salt
        new_user.password_hash = pwd_generator.generate_hashed_password(hash_salt="", new_password=password)

        self.async_session.add(new_user)
        await self.async_session.commit()
        await self.async_session.refresh(new_user)
        return new_user

    async def get_user_by_email(self, *, email: str) -> User:
        stmt = sqlalchemy.select(User).where(User.email == email)
        query = await self.async_session.execute(statement=stmt)
        user = query.scalar()
        if not user:
            raise EntityDoesNotExist("User with this email does not exist!")
        return user  # type: ignore

    async def verify_password(self, *, email: str, password: str) -> User:
        user = await self.get_user_by_email(email=email)
        if not pwd_generator.is_password_authenticated(hash_salt="", password=password, hashed_password=user.password_hash):
            raise PasswordDoesNotMatch("Password does not match!")
        return user

    async def update_resume_data(
        self,
        *,
        user_id: int,
        resume_text: str | None,
        years_experience: float | None,
        skills: list[str] | None,
    ) -> User:
        stmt = sqlalchemy.select(User).where(User.id == user_id)
        query = await self.async_session.execute(statement=stmt)
        user: User | None = query.scalar()  # type: ignore
        if not user:
            raise EntityDoesNotExist("User does not exist!")

        user.resume_text = resume_text
        user.years_experience = years_experience
        # Store skills as JSON; keep shape flexible
        user.skills = {"items": skills or []}

        await self.async_session.commit()
        await self.async_session.refresh(user)
        return user


