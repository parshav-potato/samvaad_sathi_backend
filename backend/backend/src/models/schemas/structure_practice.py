"""Schemas for structure practice endpoints."""

import datetime
import pydantic
from src.models.schemas.base import BaseSchemaModel


class StructurePracticeSessionCreate(BaseSchemaModel):
    """Request to create a structure practice session."""
    interview_id: int | None = pydantic.Field(
        default=None,
        description="Optional interview ID to practice with existing questions. If not provided, creates a new interview."
    )
    track: str | None = pydantic.Field(
        default=None,
        description="Track for the practice (used only when interview_id is not provided). Defaults to 'JavaScript Developer'."
    )
    difficulty: str | None = pydantic.Field(
        default=None,
        description="Difficulty level (used only when interview_id is not provided). Defaults to 'easy'."
    )


class StructurePracticeSessionResponse(BaseSchemaModel):
    """Response for structure practice session creation/retrieval."""
    practice_id: int
    interview_id: int | None
    track: str
    questions: list[dict]  # List of question objects with text, framework, sections, current_section
    status: str
    created_at: datetime.datetime


class StructurePracticeAnswerSubmitResponse(BaseSchemaModel):
    """Response after submitting a section answer."""
    answer_id: int
    practice_id: int
    question_index: int
    section_name: str  # Section that was just submitted
    sections_complete: int
    total_sections: int
    next_section: str | None  # Next section to record, None if all complete
    next_section_hint: str | None  # Dynamic hint for next section
    is_complete: bool  # True if all sections submitted
    message: str


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
