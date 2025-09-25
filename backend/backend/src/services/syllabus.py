"""
Syllabus and prompting helpers for interview question generation.

This module provides a clean interface for managing interview question topics,
roles, and difficulty levels. It has been refactored for better maintainability
and type safety.

Provides:
- Canonical roles and aliases mapping from free-form `track` to a target role
- Topic banks per role and difficulty for 'tech' and 'tech_allied'
- Behavioral topics list (from product requirements)
- Ratio helper to split the 5 questions into tech/tech_allied/behavioral buckets

Usage:
    from src.services.syllabus import syllabus_service
    
    # Get topics for a role
    topics = syllabus_service.get_topics_for_role("react", "medium")
    
    # Compute question ratio
    ratio = syllabus_service.compute_question_ratio(years_experience=2.0)
    
    # Extract tech skills from resume
    skills = syllabus_service.extract_tech_allied_from_resume(resume_text)
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .syllabus_service import syllabus_service
from .syllabus_data import CANONICAL_ROLES, ROLE_ALIASES
from .syllabus_content import SYLLABUS


def derive_role(track: str) -> str:
    """
    Derive canonical role from track string.
    
    Args:
        track: Input track string (e.g., "react", "frontend")
        
    Returns:
        Canonical role name
        
    Note:
        This function is maintained for backward compatibility.
        Consider using syllabus_service.derive_role() for new code.
    """
    return syllabus_service._role_manager.derive_role(track)


def get_topics_for(role: str, difficulty: str) -> Dict[str, List[str]]:
    """
    Get topics for a specific role and difficulty.
    
    Args:
        role: Role name (can be alias or canonical)
        difficulty: Difficulty level ("easy", "medium", "hard")
        
    Returns:
        Dictionary containing topics by category
        
    Note:
        This function is maintained for backward compatibility.
        Consider using syllabus_service.get_topics_for_role() for new code.
    """
    topic_bank = syllabus_service.get_topics_for_role(role, difficulty)
    return {
        "tech": topic_bank.tech,
        "tech_allied": topic_bank.tech_allied,
        "behavioral": topic_bank.behavioral,
        "archetypes": topic_bank.archetypes,
        "depth_guidelines": topic_bank.depth_guidelines,
    }


def compute_category_ratio(
    years_experience: Optional[float] = None, 
    has_resume_text: bool = False, 
    has_skills: bool = False
) -> Dict[str, int]:
    """
    Compute question distribution ratio based on candidate profile.
    
    Args:
        years_experience: Years of professional experience
        has_resume_text: Whether resume text is available
        has_skills: Whether skills are extracted from resume
        
    Returns:
        Dictionary with question counts by category
        
    Note:
        This function is maintained for backward compatibility.
        Consider using syllabus_service.compute_question_ratio() for new code.
    """
    ratio = syllabus_service.compute_question_ratio(
        years_experience, has_resume_text, has_skills
    )
    return {
        "tech": ratio.tech,
        "tech_allied": ratio.tech_allied,
        "behavioral": ratio.behavioral,
    }


def tech_allied_from_resume(
    resume_text: Optional[str] = None,
    skills: Optional[List[str]] = None,
    fallback: Optional[List[str]] = None,
) -> List[str]:
    """
    Extract tech_allied topics from resume content.
    
    Args:
        resume_text: Raw resume text
        skills: Extracted skills list
        fallback: Fallback topics if extraction fails
        
    Returns:
        List of tech_allied topics
        
    Note:
        This function is maintained for backward compatibility.
        Consider using syllabus_service.extract_tech_allied_from_resume() for new code.
    """
    return syllabus_service.extract_tech_allied_from_resume(
        resume_text, skills, fallback
    )


# Export the main service for new code
__all__ = [
    "syllabus_service",
    "derive_role",
    "get_topics_for", 
    "compute_category_ratio",
    "tech_allied_from_resume",
    "CANONICAL_ROLES",
    "ROLE_ALIASES",
    "SYLLABUS",
]
