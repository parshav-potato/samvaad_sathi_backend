"""Schemas for the interview Summary Report (independent of Final Report).

This response is structured to match the UI layout shown in the provided image:
- Overall Score Summary (Knowledge Competence and Speech & Structure)
- Final Summary (Strengths and Areas of Improvement)
- Actionable Steps (Knowledge Development and Speech & Structure Fluency)

It is generated directly from per-question analyses and does not depend on
the Final Report models.
"""

from __future__ import annotations

import pydantic
from typing import List, Dict, Any

from src.models.schemas.base import BaseSchemaModel


class SummaryReportRequest(BaseSchemaModel):
    """Input to generate the summary report for a given interview."""

    interview_id: pydantic.StrictInt = pydantic.Field(gt=0)

    model_config = BaseSchemaModel.model_config.copy()
    model_config["json_schema_extra"] = {"examples": [{"interviewId": 606}]}


class KnowledgeCompetenceBreakdown(BaseSchemaModel):
    accuracy: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    depth: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    coverage: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    relevance: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)


class SpeechStructureBreakdown(BaseSchemaModel):
    pacing: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    structure: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    pauses: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    grammar: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)


class OverallScoreKnowledgeCompetence(BaseSchemaModel):
    average5pt: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    averagePct: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    breakdown: KnowledgeCompetenceBreakdown | None = None


class OverallScoreSpeechStructure(BaseSchemaModel):
    average5pt: float | None = pydantic.Field(default=None, ge=0.0, le=5.0)
    averagePct: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    breakdown: SpeechStructureBreakdown | None = None


class OverallScoreSummary(BaseSchemaModel):
    knowledgeCompetence: OverallScoreKnowledgeCompetence
    speechStructure: OverallScoreSpeechStructure


class FinalSummarySection(BaseSchemaModel):
    knowledgeRelated: List[str] = pydantic.Field(default_factory=list)
    speechFluencyRelated: List[str] = pydantic.Field(default_factory=list)


class FinalSummary(BaseSchemaModel):
    strengths: FinalSummarySection
    areasOfImprovement: FinalSummarySection


class KnowledgeDevelopmentSteps(BaseSchemaModel):
    targetedConceptReinforcement: List[str] = pydantic.Field(default_factory=list)
    examplePractice: List[str] = pydantic.Field(default_factory=list)
    conceptualDepth: List[str] = pydantic.Field(default_factory=list)


class SpeechStructureFluencySteps(BaseSchemaModel):
    fluencyDrills: List[str] = pydantic.Field(default_factory=list)
    grammarPractice: List[str] = pydantic.Field(default_factory=list)
    structureFramework: List[str] = pydantic.Field(default_factory=list)


class ActionableSteps(BaseSchemaModel):
    knowledgeDevelopment: KnowledgeDevelopmentSteps
    speechStructureFluency: SpeechStructureFluencySteps


class ReportMetadata(BaseSchemaModel):
    totalQuestions: int = 0
    usedQuestions: int = 0
    model: str | None = None
    latencyMs: int | None = None
    generatedAt: str | None = None


class PerQuestionItem(BaseSchemaModel):
    questionAttemptId: int
    questionText: str | None = None
    keyTakeaways: List[str] = pydantic.Field(default_factory=list)
    knowledgeScorePct: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)
    speechScorePct: float | None = pydantic.Field(default=None, ge=0.0, le=100.0)


class TopicHighlights(BaseSchemaModel):
    strengthsTopics: List[str] = pydantic.Field(default_factory=list)
    improvementTopics: List[str] = pydantic.Field(default_factory=list)


class SummaryReportResponse(BaseSchemaModel):
    interview_id: int
    overallScoreSummary: OverallScoreSummary
    finalSummary: FinalSummary
    actionableSteps: ActionableSteps
    # Optional additional details
    metadata: ReportMetadata | None = None
    perQuestion: List[PerQuestionItem] = pydantic.Field(default_factory=list)
    topicHighlights: TopicHighlights | None = None
