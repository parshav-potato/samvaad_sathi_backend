"""Schemas for speech pacing practice endpoints."""

import datetime
import pydantic
from typing import Optional

from src.models.schemas.base import BaseSchemaModel


class PacingPracticeSessionCreateRequest(BaseSchemaModel):
    """Request body for creating a new pacing practice session."""
    level: int = pydantic.Field(
        ...,
        ge=1,
        le=3,
        description="Difficulty level: 1 = Sentence Control, 2 = Paragraph Fluency, 3 = Interview Mastery",
    )


class PacingPracticeSessionResponse(BaseSchemaModel):
    """Response returned when a new pacing practice session is created."""
    session_id: int
    level: int
    level_name: str
    prompt_text: str
    status: str
    created_at: datetime.datetime


class PacingAnalysisMetric(BaseSchemaModel):
    """A single measured metric with its status and contextual feedback."""
    value: float
    ideal_range: str
    status: str          # "Good" | "Needs Adjustment"
    feedback: str


class PacingPracticeSubmitResponse(BaseSchemaModel):
    """Response returned after audio is submitted and analysed."""
    session_id: int
    level: int
    score: int           # 0-100
    score_label: str     # e.g. "Good Progress! Keep Practicing"
    speech_speed: PacingAnalysisMetric
    pause_distribution: PacingAnalysisMetric
    level_unlocked: Optional[int] = None   # 2 or 3 if this attempt unlocked a new level


class PacingLevelStatus(BaseSchemaModel):
    """Status of a single pacing practice level for the dashboard."""
    level: int
    name: str
    description: str
    status: str              # "locked" | "in_progress" | "complete"
    best_score: Optional[int] = None
    unlock_threshold: int    # score needed to unlock the NEXT level
    unlock_message: str      # e.g. "Unlock level-2 at 90%"


class PacingLevelsResponse(BaseSchemaModel):
    """Full dashboard data: all three levels + overall readiness."""
    levels: list[PacingLevelStatus]
    overall_readiness: int   # 0-100 percentage


class PacingPracticeSessionDetailResponse(BaseSchemaModel):
    """Full details of a completed pacing practice session."""
    session_id: int
    level: int
    level_name: str
    prompt_text: str
    status: str
    transcript: Optional[str] = None
    score: Optional[int] = None
    speech_speed: Optional[PacingAnalysisMetric] = None
    pause_distribution: Optional[PacingAnalysisMetric] = None
    analysis_result: Optional[dict] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
