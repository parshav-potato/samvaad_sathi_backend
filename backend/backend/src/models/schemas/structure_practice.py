"""Schemas for structure practice endpoints."""

import datetime
import pydantic
from src.models.schemas.base import BaseSchemaModel


class StructurePracticeSessionCreate(BaseSchemaModel):
    """Request to create a structure practice session."""
    interview_id: int | None = pydantic.Field(
        default=None,
        description="Optional interview ID to practice with existing questions. If not provided, uses generic questions."
    )


class StructurePracticeSessionResponse(BaseSchemaModel):
    """Response for structure practice session creation/retrieval."""
    practice_id: int
    interview_id: int | None
    track: str
    questions: list[dict]  # List of question objects with text, hint, index
    status: str
    created_at: datetime.datetime


class StructurePracticeAnswerSubmitResponse(BaseSchemaModel):
    """Response after submitting an answer."""
    answer_id: int
    practice_id: int
    question_index: int
    status: str = "submitted"
    message: str = "Answer submitted successfully. Call analyze endpoint to get feedback."


class FrameworkSection(BaseSchemaModel):
    """Individual framework section status."""
    name: str  # e.g., "Context", "Theory", "Example", etc.
    status: str  # "completed", "incomplete"
    answer_recorded: bool
    time_spent_seconds: int | None = None


class FrameworkProgress(BaseSchemaModel):
    """Framework progress breakdown."""
    framework_name: str  # e.g., "C-T-E-T-D"
    sections: list[FrameworkSection]
    completion_percentage: int  # 0-100
    sections_complete: int
    total_sections: int
    progress_message: str  # e.g., "Good Progress!", "Almost There!"


class TimePerSection(BaseSchemaModel):
    """Time spent per framework section."""
    section_name: str
    seconds: int


class StructurePracticeAnalysisResponse(BaseSchemaModel):
    """Response from analyzing a structure practice answer."""
    answer_id: int
    practice_id: int
    question_index: int
    
    # Main analysis results
    framework_progress: FrameworkProgress
    time_per_section: list[TimePerSection]
    key_insight: str
    
    # Metadata
    analyzed_at: datetime.datetime
    llm_model: str | None = None
    llm_latency_ms: int | None = None


class StructurePracticeListResponse(BaseSchemaModel):
    """Response for listing structure practice sessions."""
    practices: list[StructurePracticeSessionResponse]
    total: int
