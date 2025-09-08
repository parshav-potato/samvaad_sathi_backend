from __future__ import annotations

from typing import Optional

from sqlalchemy import select

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
        existing = await self.get_by_interview_id(interview_id)
        if existing:
            existing.summary = summary
            existing.knowledge_competence = knowledge_competence
            existing.speech_structure_fluency = speech_structure_fluency
            existing.overall_score = overall_score
            await self.async_session.flush()
            return existing

        report = Report(
            interview_id=interview_id,
            summary=summary,
            knowledge_competence=knowledge_competence,
            speech_structure_fluency=speech_structure_fluency,
            overall_score=overall_score,
        )
        self.async_session.add(report)
        await self.async_session.flush()
        return report
