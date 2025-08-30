import datetime

from src.models.schemas.base import BaseSchemaModel


class QuestionItem(BaseSchemaModel):
    text: str
    topic: str | None = None
    difficulty: str | None = None


class InterviewCreate(BaseSchemaModel):
    track: str
    difficulty: str | None = None  # easy | medium | hard


class GenerateQuestionsRequest(BaseSchemaModel):
    use_resume: bool = True  # Whether to use resume text for question generation


class InterviewInResponse(BaseSchemaModel):
    id: int
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
    id: int
    track: str
    difficulty: str
    status: str
    created_at: datetime.datetime


class InterviewsListResponse(BaseSchemaModel):
    items: list[InterviewItem]
    next_cursor: int | None
    limit: int


class QuestionAttemptItem(BaseSchemaModel):
    id: int
    question_text: str
    audio_url: str | None = None
    transcription: dict | None = None
    created_at: datetime.datetime


class QuestionsListResponse(BaseSchemaModel):
    interview_id: int
    items: list[str]
    next_cursor: int | None
    limit: int


class QuestionAttemptsListResponse(BaseSchemaModel):
    interview_id: int
    items: list[QuestionAttemptItem]
    next_cursor: int | None
    limit: int


