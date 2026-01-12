"""CRUD repository for pronunciation practice sessions."""

import sqlalchemy
import json
import random
from pathlib import Path
from typing import Optional

from src.models.db.pronunciation_practice import PronunciationPractice
from src.repository.crud.base import BaseCRUDRepository


class PronunciationPracticeCRUDRepository(BaseCRUDRepository):
    """Repository for pronunciation practice CRUD operations."""
    
    _word_bank: dict | None = None
    
    @classmethod
    def _load_word_bank(cls) -> dict:
        """Load word bank from JSON file (cached)."""
        if cls._word_bank is not None:
            return cls._word_bank
        
        # Load from pronunciation_words.json
        words_file = Path(__file__).parent.parent.parent / "data" / "pronunciation_words.json"
        with open(words_file, "r", encoding="utf-8") as f:
            cls._word_bank = json.load(f)
        
        return cls._word_bank
    
    async def create_practice_session(
        self,
        *,
        user_id: int,
        difficulty: str,
    ) -> PronunciationPractice:
        """
        Create a new pronunciation practice session with 10 random words.
        
        Args:
            user_id: The user creating the practice session
            difficulty: Difficulty level (easy, medium, hard)
        
        Returns:
            Created PronunciationPractice instance
        """
        # Load word bank
        word_bank = self._load_word_bank()
        
        # Get words for the selected difficulty
        available_words = word_bank.get(difficulty, [])
        if not available_words:
            raise ValueError(f"No words available for difficulty: {difficulty}")
        
        # Select 10 random words
        selected_words = random.sample(available_words, min(10, len(available_words)))
        
        # Create practice session
        practice = PronunciationPractice(
            user_id=user_id,
            difficulty=difficulty,
            words=selected_words,  # Store as JSONB
            status="active",
        )
        
        self.async_session.add(practice)
        await self.async_session.commit()
        await self.async_session.refresh(practice)
        
        return practice
    
    async def get_by_id(self, *, practice_id: int) -> Optional[PronunciationPractice]:
        """Get a pronunciation practice session by ID."""
        stmt = sqlalchemy.select(PronunciationPractice).where(
            PronunciationPractice.id == practice_id
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()
    
    async def get_by_id_and_user(
        self,
        *,
        practice_id: int,
        user_id: int,
    ) -> Optional[PronunciationPractice]:
        """Get a pronunciation practice session by ID and user ID."""
        stmt = (
            sqlalchemy.select(PronunciationPractice)
            .where(PronunciationPractice.id == practice_id)
            .where(PronunciationPractice.user_id == user_id)
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()
    
    async def list_by_user(self, *, user_id: int, limit: int = 10) -> list[PronunciationPractice]:
        """List pronunciation practice sessions for a user."""
        stmt = (
            sqlalchemy.select(PronunciationPractice)
            .where(PronunciationPractice.user_id == user_id)
            .order_by(PronunciationPractice.created_at.desc())
            .limit(limit)
        )
        query = await self.async_session.execute(statement=stmt)
        return list(query.scalars().all())
