"""Analysis request and response models for aggregated analysis endpoints."""

import pydantic
from typing import List, Dict, Any

from src.models.schemas.base import BaseSchemaModel


class CompleteAnalysisRequest(BaseSchemaModel):
    """Request model for complete analysis endpoint"""
    question_attempt_id: int = pydantic.Field(description="ID of the question attempt to analyze")
    analysis_types: List[str] = pydantic.Field(
        default=["domain", "communication", "pace", "pause"],
        description="List of analysis types to perform. Available: domain, communication, pace, pause"
    )

    @pydantic.field_validator("analysis_types")
    @classmethod
    def validate_analysis_types(cls, v: List[str]) -> List[str]:
        allowed_types = {"domain", "communication", "pace", "pause"}
        invalid_types = set(v) - allowed_types
        if invalid_types:
            raise ValueError(f"Invalid analysis types: {invalid_types}. Allowed: {allowed_types}")
        return v


class AnalysisMetadata(BaseSchemaModel):
    """Metadata about the analysis process"""
    total_latency_ms: int = pydantic.Field(description="Total time taken for all analyses in milliseconds")
    completed_analyses: List[str] = pydantic.Field(description="List of successfully completed analysis types")
    failed_analyses: List[str] = pydantic.Field(description="List of failed analysis types")
    partial_failure: bool = pydantic.Field(description="Whether some analyses failed while others succeeded")


class AggregatedAnalysis(BaseSchemaModel):
    """Container for all analysis results"""
    domain: Dict[str, Any] | None = pydantic.Field(default=None, description="Domain knowledge analysis results")
    communication: Dict[str, Any] | None = pydantic.Field(default=None, description="Communication quality analysis results")
    pace: Dict[str, Any] | None = pydantic.Field(default=None, description="Speaking pace analysis results")
    pause: Dict[str, Any] | None = pydantic.Field(default=None, description="Pause pattern analysis results")


class CompleteAnalysisResponse(BaseSchemaModel):
    """Response model for complete analysis endpoint"""
    question_attempt_id: int = pydantic.Field(description="ID of the analyzed question attempt")
    analysis_complete: bool = pydantic.Field(description="Whether all requested analyses completed successfully")
    aggregated_analysis: AggregatedAnalysis = pydantic.Field(description="Combined analysis results from all types")
    metadata: AnalysisMetadata = pydantic.Field(description="Analysis process metadata and timing information")
    saved: bool = pydantic.Field(description="Whether the aggregated analysis was successfully saved to database")
    save_error: str | None = pydantic.Field(default=None, description="Error message if database save failed")
    message: str = pydantic.Field(description="Human-friendly status message about the analysis process")


# Individual analysis response models for internal use
class DomainAnalysisResponse(BaseSchemaModel):
    """Response from domain analysis endpoint"""
    question_attempt_id: int
    domain_score: float = pydantic.Field(ge=0.0, le=100.0)
    domain_feedback: str
    knowledge_areas: List[str]
    strengths: List[str]
    improvements: List[str]


class CommunicationAnalysisResponse(BaseSchemaModel):
    """Response from communication analysis endpoint"""
    question_attempt_id: int
    communication_score: float = pydantic.Field(ge=0.0, le=100.0)
    clarity_score: float = pydantic.Field(ge=0.0, le=100.0)
    vocabulary_score: float = pydantic.Field(ge=0.0, le=100.0)
    grammar_score: float = pydantic.Field(ge=0.0, le=100.0)
    structure_score: float = pydantic.Field(ge=0.0, le=100.0)
    communication_feedback: str
    recommendations: List[str]


class PaceAnalysisResponse(BaseSchemaModel):
    """Response from pace analysis endpoint"""
    question_attempt_id: int
    pace_score: float = pydantic.Field(ge=0.0, le=100.0)
    words_per_minute: float
    pace_feedback: str
    pace_category: str  # "too_slow", "optimal", "too_fast"
    recommendations: List[str]


class PauseAnalysisResponse(BaseSchemaModel):
    """Response from pause analysis endpoint"""
    question_attempt_id: int
    pause_score: float = pydantic.Field(ge=0.0, le=100.0)
    total_pause_duration: float
    pause_count: int
    average_pause_duration: float
    longest_pause_duration: float
    pause_feedback: str
    recommendations: List[str]
