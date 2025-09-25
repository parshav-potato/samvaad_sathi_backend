import datetime

import pydantic

from src.models.schemas.base import BaseSchemaModel


class InterviewQuestionOut(BaseSchemaModel):
    interview_question_id: int = pydantic.Field(description="Unique identifier for the interview question")
    text: str
    topic: str | None = None
    status: str


class CreateAttemptResponse(BaseSchemaModel):
    question_attempt_id: int


class CreateAttemptRequest(BaseSchemaModel):
    interview_id: int
    question_id: int

    # Swagger example
    model_config = BaseSchemaModel.model_config.copy()
    model_config["json_schema_extra"] = {
        "examples": [
            {"interviewId": 123, "questionId": 456}
        ]
    }


class QuestionItem(BaseSchemaModel):
    interview_question_id: int | None = None
    text: str
    topic: str | None = None
    difficulty: str | None = None
    category: str | None = None


class InterviewCreate(BaseSchemaModel):
    track: str
    difficulty: str | None = None  # easy | medium | hard


class GenerateQuestionsRequest(BaseSchemaModel):
    interview_id: int | None = None
    use_resume: bool = True  # Whether to use resume text for question generation
    
    # Swagger example
    model_config = BaseSchemaModel.model_config.copy()
    model_config["json_schema_extra"] = {
        "examples": [
            {"useResume": True},
            {"interviewId": 123, "useResume": True}
        ]
    }


class InterviewInResponse(BaseSchemaModel):
    interview_id: int = pydantic.Field(description="Unique identifier for the interview")
    track: str
    difficulty: str
    status: str
    created_at: datetime.datetime
    resumed: bool


class GeneratedQuestionsInResponse(BaseSchemaModel):
    interview_id: int
    track: str
    count: int
    questions: list[str]
    question_ids: list[int] | None = None  # Include question IDs for consistency with get-questions endpoint
    items: list[QuestionItem] | None = None
    cached: bool | None = None
    llm_model: str | None = None
    llm_latency_ms: int | None = None
    llm_error: str | None = None


class InterviewItem(BaseSchemaModel):
    interview_id: int = pydantic.Field(description="Unique identifier for the interview")
    track: str
    difficulty: str
    status: str
    created_at: datetime.datetime


class InterviewItemWithSummary(BaseSchemaModel):
    """Enhanced interview item that includes summary report data for completed interviews."""
    interview_id: int = pydantic.Field(description="Unique identifier for the interview")
    track: str
    difficulty: str
    status: str
    created_at: datetime.datetime
    knowledge_percentage: float | None = pydantic.Field(default=None, ge=0.0, le=100.0, description="Knowledge competence percentage from summary report")
    speech_fluency_percentage: float | None = pydantic.Field(default=None, ge=0.0, le=100.0, description="Speech fluency percentage from summary report")
    summary_report_available: bool = pydantic.Field(default=False, description="Whether a summary report exists for this interview")


class InterviewsListResponse(BaseSchemaModel):
    items: list[InterviewItem]
    next_cursor: int | None
    limit: int


class InterviewsListWithSummaryResponse(BaseSchemaModel):
    """Enhanced interviews list response that includes summary report data."""
    items: list[InterviewItemWithSummary]
    next_cursor: int | None
    limit: int


class QuestionAttemptItem(BaseSchemaModel):
    question_attempt_id: int = pydantic.Field(description="Unique identifier for the question attempt")
    question_text: str
    question_id: int | None = None
    audio_url: str | None = None
    transcription: dict | None = None
    created_at: datetime.datetime


class QuestionsListResponse(BaseSchemaModel):
    interview_id: int
    items: list[InterviewQuestionOut]
    next_cursor: int | None
    limit: int


class QuestionAttemptsListResponse(BaseSchemaModel):
    interview_id: int
    items: list[QuestionAttemptItem]
    next_cursor: int | None
    limit: int


class CompleteInterviewRequest(BaseSchemaModel):
    interview_id: int


