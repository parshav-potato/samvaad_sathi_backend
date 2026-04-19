import sqlalchemy

from src.models.db.job_profile import JobProfile
from src.repository.crud.base import BaseCRUDRepository


class JobProfileCRUDRepository(BaseCRUDRepository):
    async def create(
        self,
        *,
        job_name: str,
        job_description: str,
        company_name: str | None,
        experience_level: str | None,
        skills: list[str] | None,
        additional_context: str | None,
        created_by: int | None,
    ) -> JobProfile:
        profile = JobProfile(
            job_name=job_name,
            job_description=job_description,
            company_name=company_name,
            experience_level=experience_level,
            skills=skills,
            additional_context=additional_context,
            created_by=created_by,
        )
        self.async_session.add(profile)
        await self.async_session.commit()
        await self.async_session.refresh(profile)
        return profile

    async def list_all(self) -> list[JobProfile]:
        stmt = sqlalchemy.select(JobProfile).order_by(JobProfile.id.desc())
        query = await self.async_session.execute(statement=stmt)
        return list(query.scalars().all())

    async def get_by_id(self, *, job_profile_id: int) -> JobProfile | None:
        stmt = sqlalchemy.select(JobProfile).where(JobProfile.id == job_profile_id)
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()

    async def delete(self, *, job_profile_id: int) -> bool:
        stmt = sqlalchemy.select(JobProfile).where(JobProfile.id == job_profile_id)
        query = await self.async_session.execute(statement=stmt)
        profile = query.scalar_one_or_none()
        if profile is None:
            return False

        await self.async_session.delete(profile)
        await self.async_session.commit()
        return True
