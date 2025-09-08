"""Schemas for session-level (interview) final report.

These models define the request/response shapes for the /final-report endpoint
and mirror the structure of the Report DB model (summary, knowledge_competence,
speech_structure_fluency, overall_score). They are designed to be populated by
an aggregation service that reads per-question analyses from QuestionAttempt.
"""

from __future__ import annotations

import pydantic
from typing import Any, Dict, List

from src.models.schemas.base import BaseSchemaModel


class FinalReportRequest(BaseSchemaModel):
    """Request model to generate or fetch a final report for an interview."""

    interview_id: pydantic.StrictInt = pydantic.Field(
        gt=0, description="ID of the interview session to generate the final report for (must be > 0)"
    )


class PerQuestionAnalysisSummary(BaseSchemaModel):
    """Condensed view of per-question analysis for inclusion in the report summary."""

    question_attempt_id: pydantic.StrictInt = pydantic.Field(
        gt=0, description="QuestionAttempt ID (must be > 0)"
    )
    question_text: str | None = None

    # Aggregated/primary scores
    domain_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    communication_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    pace_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    pause_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)

    strengths: List[str] = pydantic.Field(default_factory=list)
    improvements: List[str] = pydantic.Field(default_factory=list)


class ReportSummary(BaseSchemaModel):
    """High-level summary content for the report, including per-question rollup."""

    title: str = pydantic.Field(default="Interview Performance Summary")
    overview: str = pydantic.Field(
        default="", description="Narrative overview of the interview performance"
    )
    per_question: List[PerQuestionAnalysisSummary] = pydantic.Field(
        default_factory=list, description="Per-question condensed analysis items"
    )


class KnowledgeCompetenceSection(BaseSchemaModel):
    """Knowledge and competence metrics aggregated across questions."""

    average_domain_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    coverage_topics: List[str] = pydantic.Field(default_factory=list)
    strengths: List[str] = pydantic.Field(default_factory=list)
    improvements: List[str] = pydantic.Field(default_factory=list)
    details: Dict[str, Any] | None = pydantic.Field(
        default=None, description="Optional extra metrics or breakdowns"
    )


class SpeechStructureFluencySection(BaseSchemaModel):
    """Speech quality, structure, and fluency metrics aggregated across questions."""

    average_communication_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    average_pace_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    average_pause_score: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)

    # Optional sub-metrics averaged when available
    clarity: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    vocabulary: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    grammar: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    structure: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)

    recommendations: List[str] = pydantic.Field(default_factory=list)
    details: Dict[str, Any] | None = pydantic.Field(
        default=None, description="Optional extra metrics or breakdowns"
    )


class FinalReportResponse(BaseSchemaModel):
    """Response model for the final session report."""

    interview_id: int
    summary: ReportSummary
    knowledge_competence: KnowledgeCompetenceSection
    speech_structure_fluency: SpeechStructureFluencySection
    overall_score: float = pydantic.Field(ge=0.0, le=100.0)

    # Process metadata
    saved: bool = pydantic.Field(description="Whether the report was persisted to database")
    save_error: str | None = pydantic.Field(default=None, description="Error when persisting the report")
    message: str = pydantic.Field(description="Status message about report generation")
