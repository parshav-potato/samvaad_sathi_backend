from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db.report import Report
from src.repository.crud.base import BaseCRUDRepository


class ReportCRUDRepository(BaseCRUDRepository):
    async def get_by_interview_id(self, interview_id: int) -> Optional[Report]:
        stmt = select(Report).where(Report.interview_id == interview_id)
        res = await self.async_session.execute(stmt)
        return res.scalars().first()

    async def upsert_report(
        self,
        interview_id: int,
        summary: dict | None,
        knowledge_competence: dict | None,
        speech_structure_fluency: dict | None,
        overall_score: float | None,
    ) -> Report:
        # Atomic upsert keyed on interview_id using PostgreSQL ON CONFLICT
        stmt = (
            pg_insert(Report)
            .values(
                interview_id=interview_id,
                summary=summary,
                knowledge_competence=knowledge_competence,
                speech_structure_fluency=speech_structure_fluency,
                overall_score=overall_score,
            )
            .on_conflict_do_update(
                index_elements=[Report.interview_id],
                set_={
                    "summary": summary,
                    "knowledge_competence": knowledge_competence,
                    "speech_structure_fluency": speech_structure_fluency,
                    "overall_score": overall_score,
                },
            )
            .returning(Report)
        )

        result = await self.async_session.execute(stmt)
        # Returning a mapped Report instance
        obj = result.scalar_one()
        return obj
