from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.db.summary_report import SummaryReport
from src.repository.crud.base import BaseCRUDRepository


class SummaryReportCRUDRepository(BaseCRUDRepository):
    async def get_by_interview_id(self, interview_id: int) -> Optional[SummaryReport]:
        stmt = select(SummaryReport).where(SummaryReport.interview_id == interview_id)
        res = await self.async_session.execute(stmt)
        return res.scalars().first()

    async def upsert(
        self,
        interview_id: int,
        report_json: dict | None,
    ) -> SummaryReport:
        stmt = (
            pg_insert(SummaryReport)
            .values(interview_id=interview_id, report_json=report_json)
            .on_conflict_do_update(index_elements=[SummaryReport.interview_id], set_={"report_json": report_json})
            .returning(SummaryReport)
        )
        res = await self.async_session.execute(stmt)
        return res.scalar_one()
