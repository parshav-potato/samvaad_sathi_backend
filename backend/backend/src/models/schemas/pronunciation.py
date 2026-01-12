"""Schemas for pronunciation practice endpoints."""

from __future__ import annotations
import datetime
import pydantic

from src.models.schemas.base import BaseSchemaModel


class PronunciationPracticeCreate(BaseSchemaModel):
    """Request schema for creating a pronunciation practice session."""
    difficulty: str = pydantic.Field(description="Difficulty level: easy, medium, or hard")

    model_config = BaseSchemaModel.model_config.copy()
    model_config["json_schema_extra"] = {
        "examples": [
            {"difficulty": "easy"},
            {"difficulty": "medium"},
            {"difficulty": "hard"}
        ]
    }


class PronunciationWord(BaseSchemaModel):
    """Schema for a pronunciation practice word."""
    index: int = pydantic.Field(description="0-based index of the word in the practice session")
    word: str = pydantic.Field(description="The word to practice")
    phonetic: str = pydantic.Field(description="Phonetic pronunciation guide")


class PronunciationPracticeResponse(BaseSchemaModel):
    """Response schema for pronunciation practice session."""
    practice_id: int = pydantic.Field(description="Unique identifier for the practice session")
    difficulty: str = pydantic.Field(description="Difficulty level")
    words: list[PronunciationWord] = pydantic.Field(description="List of 10 words to practice")
    total_words: int = pydantic.Field(description="Total number of words (always 10)")
    status: str = pydantic.Field(description="Session status (active, completed)")
    created_at: datetime.datetime = pydantic.Field(description="Session creation timestamp")


class PronunciationAudioRequest(BaseSchemaModel):
    """Request schema for generating pronunciation audio."""
    practice_id: int = pydantic.Field(description="Practice session ID")
    question_number: int = pydantic.Field(ge=0, le=9, description="Question index (0-9)")
    slow: bool = pydantic.Field(default=False, description="Whether to generate slow-paced audio")

    model_config = BaseSchemaModel.model_config.copy()
    model_config["json_schema_extra"] = {
        "examples": [
            {"practice_id": 1, "question_number": 0, "slow": False},
            {"practice_id": 1, "question_number": 5, "slow": True}
        ]
    }
