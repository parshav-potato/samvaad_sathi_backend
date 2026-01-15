#!/usr/bin/env python3
"""Check structure practice answers in database."""

import asyncio
import sys
sys.path.insert(0, "/home/parshav-potato/projects/samvaad_sathi_backend/backend/backend")

from sqlalchemy import select
from src.repository.database import async_db
from src.models.db.structure_practice import StructurePracticeAnswer

async def check_answers():
    session = async_db.get_session()
    async with session:
        stmt = select(StructurePracticeAnswer).order_by(StructurePracticeAnswer.created_at.desc()).limit(20)
        result = await session.execute(stmt)
        answers = result.scalars().all()
        
        print(f"Found {len(answers)} answers in database:")
        print(f"{'ID':<5} {'Practice':<10} {'Q#':<5} {'Section':<15} {'Answer Preview':<40} {'Created'}")
        print("-" * 100)
        
        for ans in answers:
            preview = ans.answer_text[:37] + "..." if len(ans.answer_text) > 40 else ans.answer_text
            print(f"{ans.id:<5} {ans.practice_id:<10} {ans.question_index:<5} {ans.section_name:<15} {preview:<40} {ans.created_at}")

if __name__ == "__main__":
    asyncio.run(check_answers())
