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


class QuestionItem(BaseSchemaModel):
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


class InterviewsListResponse(BaseSchemaModel):
    items: list[InterviewItem]
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


