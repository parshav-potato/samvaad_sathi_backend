"""Service to aggregate per-question analyses into a session-level final report.

This service reads QuestionAttempt.analysis_json for an interview, aggregates
scores and insights, and returns data that fits FinalReportResponse. Initial
version computes simple averages and collects strengths/improvements; LLM
summary generation can be added later if needed.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.question_attempt import QuestionAttempt
from src.models.schemas.report import (
    FinalReportResponse,
    KnowledgeCompetenceSection,
    PerQuestionAnalysisSummary,
    ReportSummary,
    SpeechStructureFluencySection,
)


class FinalReportService:
    def __init__(self, db: SQLAlchemyAsyncSession) -> None:
        self._db = db

    async def generate_for_interview(
        self, interview_id: int, question_attempts: Iterable[QuestionAttempt]
    ) -> Dict[str, Any]:
        """Build a dict matching FinalReportResponse (without saved/save_error/message).

        Note: Persistence is expected to be handled by the repository/route.
        """

        per_question: List[PerQuestionAnalysisSummary] = []

        domain_scores: List[float] = []
        comm_scores: List[float] = []
        pace_scores: List[float] = []
        pause_scores: List[float] = []

        clarity_list: List[float] = []
        vocabulary_list: List[float] = []
        grammar_list: List[float] = []
        structure_list: List[float] = []

        coverage_topics: List[str] = []
        kc_strengths: List[str] = []
        kc_improvements: List[str] = []

        ssf_recs: List[str] = []

        for qa in question_attempts:
            qtext: Optional[str] = getattr(qa, "question_text", None)
            analysis: Dict[str, Any] = getattr(qa, "analysis_json", None) or {}

            # Domain
            d = analysis.get("domain") or {}
            d_score = _as_float(d.get("domain_score"))
            if d_score is not None:
                domain_scores.append(d_score)
            d_strengths = _as_list_str(d.get("strengths"))
            d_improvements = _as_list_str(d.get("improvements"))
            topics = _as_list_str(d.get("knowledge_areas"))
            if topics:
                coverage_topics.extend([t for t in topics if t])

            # Communication
            c = analysis.get("communication") or {}
            c_score = _as_float(c.get("communication_score"))
            if c_score is not None:
                comm_scores.append(c_score)
            for k, target in (
                ("clarity_score", clarity_list),
                ("vocabulary_score", vocabulary_list),
                ("grammar_score", grammar_list),
                ("structure_score", structure_list),
            ):
                v = _as_float(c.get(k))
                if v is not None:
                    target.append(v)

            # Pace/Pause
            p = analysis.get("pace") or {}
            p_score = _as_float(p.get("pace_score"))
            if p_score is not None:
                pace_scores.append(p_score)

            z = analysis.get("pause") or {}
            z_score = _as_float(z.get("pause_score"))
            if z_score is not None:
                pause_scores.append(z_score)

            # Merge strengths/improvements
            strengths = list(dict.fromkeys((d_strengths or []) + _as_list_str(c.get("recommendations"))))
            improvements = list(dict.fromkeys((d_improvements or []) + _as_list_str(p.get("recommendations")) + _as_list_str(z.get("recommendations"))))

            if d_strengths:
                kc_strengths.extend([s for s in d_strengths if s])
            if d_improvements:
                kc_improvements.extend([s for s in d_improvements if s])
            ssf_recs.extend(_as_list_str(c.get("recommendations")))

            per_question.append(
                PerQuestionAnalysisSummary(
                    question_attempt_id=qa.id,
                    question_text=qtext,
                    domain_score=d_score,
                    communication_score=c_score,
                    pace_score=p_score,
                    pause_score=z_score,
                    strengths=strengths,
                    improvements=improvements,
                )
            )

        summary = ReportSummary(
            overview="",  # Placeholder; can be filled by LLM in a later iteration
            per_question=per_question,
        )

        knowledge = KnowledgeCompetenceSection(
            average_domain_score=_avg(domain_scores),
            coverage_topics=_unique_preserve_order([t for t in coverage_topics if t]),
            strengths=_unique_preserve_order([s for s in kc_strengths if s]),
            improvements=_unique_preserve_order([s for s in kc_improvements if s]),
            details=None,
        )

        speech = SpeechStructureFluencySection(
            average_communication_score=_avg(comm_scores),
            average_pace_score=_avg(pace_scores),
            average_pause_score=_avg(pause_scores),
            clarity=_avg(clarity_list),
            vocabulary=_avg(vocabulary_list),
            grammar=_avg(grammar_list),
            structure=_avg(structure_list),
            recommendations=_unique_preserve_order([r for r in ssf_recs if r]),
            details=None,
        )

        # Simple overall score as average of available section scores
        section_scores: List[float] = [
            v
            for v in (
                knowledge.average_domain_score,
                speech.average_communication_score,
                speech.average_pace_score,
                speech.average_pause_score,
            )
            if v is not None
        ]
        overall = _avg(section_scores) or 0.0

        return {
            "interview_id": interview_id,
            "summary": summary.model_dump(),
            "knowledge_competence": knowledge.model_dump(),
            "speech_structure_fluency": speech.model_dump(),
            "overall_score": overall,
        }


def _as_float(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _as_list_str(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    return [str(v)]


def _avg(nums: List[float]) -> Optional[float]:
    return sum(nums) / len(nums) if nums else None


def _unique_preserve_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            out.append(it)
    return out
