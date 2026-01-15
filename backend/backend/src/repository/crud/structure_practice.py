"""CRUD repository for structure practice sessions and answers."""

import sqlalchemy
from typing import Optional
from datetime import datetime

from src.models.db.structure_practice import StructurePractice, StructurePracticeAnswer
from src.repository.crud.base import BaseCRUDRepository


class StructurePracticeCRUDRepository(BaseCRUDRepository):
    """Repository for structure practice CRUD operations."""
    
    async def create_practice_session(
        self,
        *,
        user_id: int,
        interview_id: int | None,
        track: str,
        questions: list[dict],
    ) -> StructurePractice:
        """
        Create a new structure practice session.
        
        Args:
            user_id: The user creating the practice session
            interview_id: Optional interview ID if practicing from an interview
            track: Interview track (e.g., "Software Engineering", "Data Science")
            questions: List of question dicts with text, hint, etc.
        
        Returns:
            Created StructurePractice instance
        """
        practice = StructurePractice(
            user_id=user_id,
            interview_id=interview_id,
            track=track,
            questions=questions,
            status="active",
        )
        
        self.async_session.add(practice)
        await self.async_session.commit()
        await self.async_session.refresh(practice)
        
        return practice
    
    async def get_by_id(self, *, practice_id: int) -> Optional[StructurePractice]:
        """Get a structure practice session by ID."""
        stmt = sqlalchemy.select(StructurePractice).where(
            StructurePractice.id == practice_id
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()
    
    async def get_by_id_and_user(
        self,
        *,
        practice_id: int,
        user_id: int,
    ) -> Optional[StructurePractice]:
        """Get a structure practice session by ID and user ID."""
        stmt = (
            sqlalchemy.select(StructurePractice)
            .where(StructurePractice.id == practice_id)
            .where(StructurePractice.user_id == user_id)
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()
    
    async def list_by_user(self, *, user_id: int, limit: int = 20) -> list[StructurePractice]:
        """List structure practice sessions for a user."""
        stmt = (
            sqlalchemy.select(StructurePractice)
            .where(StructurePractice.user_id == user_id)
            .order_by(StructurePractice.created_at.desc())
            .limit(limit)
        )
        query = await self.async_session.execute(statement=stmt)
        return list(query.scalars().all())
    
    async def update_status(
        self,
        *,
        practice_id: int,
        status: str,
    ) -> Optional[StructurePractice]:
        """Update practice session status."""
        stmt = (
            sqlalchemy.update(StructurePractice)
            .where(StructurePractice.id == practice_id)
            .values(status=status)
            .returning(StructurePractice)
        )
        query = await self.async_session.execute(statement=stmt)
        await self.async_session.commit()
        return query.scalar_one_or_none()


class StructurePracticeAnswerCRUDRepository(BaseCRUDRepository):
    """Repository for structure practice answer CRUD operations."""
    
    async def create_answer(
        self,
        *,
        practice_id: int,
        question_index: int,
        section_name: str,
        answer_text: str,
        time_spent_seconds: int | None = None,
    ) -> StructurePracticeAnswer:
        """
        Create an answer for a specific section of a practice question.
        
        Args:
            practice_id: The structure practice session ID
            question_index: Index of the question in the practice session
            section_name: Name of the framework section (e.g., "Context", "Theory")
            answer_text: The user's answer for this section
            time_spent_seconds: Time spent on this section
        
        Returns:
            Created StructurePracticeAnswer instance
        """
        # Create new answer for this section
        answer = StructurePracticeAnswer(
            practice_id=practice_id,
            question_index=question_index,
            section_name=section_name,
            answer_text=answer_text,
            time_spent_seconds=time_spent_seconds,
        )
        
        self.async_session.add(answer)
        await self.async_session.commit()
        await self.async_session.refresh(answer)
        
        return answer
    
    async def get_answer(
        self,
        *,
        practice_id: int,
        question_index: int,
    ) -> Optional[StructurePracticeAnswer]:
        """Get an answer for a specific practice question."""
        stmt = (
            sqlalchemy.select(StructurePracticeAnswer)
            .where(StructurePracticeAnswer.practice_id == practice_id)
            .where(StructurePracticeAnswer.question_index == question_index)
        )
        query = await self.async_session.execute(statement=stmt)
        return query.scalar_one_or_none()
    
    async def list_by_practice(
        self,
        *,
        practice_id: int,
    ) -> list[StructurePracticeAnswer]:
        """List all answers for a practice session."""
        stmt = (
            sqlalchemy.select(StructurePracticeAnswer)
            .where(StructurePracticeAnswer.practice_id == practice_id)
            .order_by(StructurePracticeAnswer.question_index, StructurePracticeAnswer.created_at)
        )
        query = await self.async_session.execute(statement=stmt)
        return list(query.scalars().all())
    
    async def list_by_practice_and_question(
        self,
        *,
        practice_id: int,
        question_index: int,
    ) -> list[StructurePracticeAnswer]:
        """List all section answers for a specific question in a practice session."""
        stmt = (
            sqlalchemy.select(StructurePracticeAnswer)
            .where(StructurePracticeAnswer.practice_id == practice_id)
            .where(StructurePracticeAnswer.question_index == question_index)
            .order_by(StructurePracticeAnswer.created_at)
        )
        query = await self.async_session.execute(statement=stmt)
        return list(query.scalars().all())
    
    async def update_analysis(
        self,
        *,
        answer_id: int,
        analysis_result: dict,
    ) -> Optional[StructurePracticeAnswer]:
        """Update the analysis result for an answer."""
        stmt = (
            sqlalchemy.update(StructurePracticeAnswer)
            .where(StructurePracticeAnswer.id == answer_id)
            .values(
                analysis_result=analysis_result,
                analyzed_at=datetime.utcnow(),
            )
            .returning(StructurePracticeAnswer)
        )
        query = await self.async_session.execute(statement=stmt)
        await self.async_session.commit()
        return query.scalar_one_or_none()
