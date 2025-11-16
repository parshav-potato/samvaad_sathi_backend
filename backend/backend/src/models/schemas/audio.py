import pydantic

from src.models.schemas.base import BaseSchemaModel


class AudioTranscriptionResponse(BaseSchemaModel):
    """Response model for audio transcription endpoint"""
    question_attempt_id: int = pydantic.Field(description="ID of the question attempt this audio belongs to")
    filename: str = pydantic.Field(description="Original uploaded audio filename")
    content_type: str = pydantic.Field(description="MIME type of the uploaded audio file")
    size: int = pydantic.Field(description="Audio file size in bytes (<= 25MB)")
    duration_seconds: float | None = pydantic.Field(default=None, description="Audio duration in seconds")
    audio_url: str = pydantic.Field(description="Stored audio file URL/path")
    transcription: dict | None = pydantic.Field(default=None, description="Whisper transcription with word-level timestamps")
    word_count: int | None = pydantic.Field(default=None, description="Number of words in transcription")
    whisper_model: str | None = pydantic.Field(default=None, description="Whisper model used for transcription")
    whisper_latency_ms: int | None = pydantic.Field(default=None, description="Whisper API call latency in milliseconds")
    whisper_error: str | None = pydantic.Field(default=None, description="Whisper API error message if transcription failed")
    message: str = pydantic.Field(description="Human-friendly status message")
    saved: bool = pydantic.Field(description="Whether the audio and transcription were successfully saved")
    save_error: str | None = pydantic.Field(default=None, description="Error message if save operation failed")
    follow_up_generated: bool = pydantic.Field(default=False, description="Whether a follow-up question was generated")
    follow_up_metadata: dict | None = pydantic.Field(default=None, description="Metadata about the generated follow-up question, if any")


class AudioValidationError(BaseSchemaModel):
    """Error response for audio validation failures"""
    error: str = pydantic.Field(description="Error message")
    details: str | None = pydantic.Field(default=None, description="Additional error details")
    supported_formats: list[str] = pydantic.Field(
        default=["audio/mpeg", "audio/wav", "audio/mp4", "audio/flac", "audio/x-flac"],
        description="List of supported audio MIME types"
    )
    max_size_mb: int = pydantic.Field(default=25, description="Maximum allowed file size in MB")


class TranscriptionRequest(BaseSchemaModel):
    """Request model for audio transcription"""
    question_attempt_id: int = pydantic.Field(description="ID of the question attempt")
    language: str = pydantic.Field(default="en", description="Language code for transcription (ISO 639-1)")
