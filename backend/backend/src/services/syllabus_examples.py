"""
Examples and usage patterns for the refactored syllabus service.

This module demonstrates how to use the new syllabus service architecture
for interview question generation.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from .syllabus_service import SyllabusService, TopicBank, QuestionRatio

# Configure logging for examples
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """Demonstrate basic usage of the syllabus service."""
    print("=== Basic Usage Example ===")
    
    # Create service instance
    service = SyllabusService()
    
    # Get topics for a React developer at medium difficulty
    topics = service.get_topics_for_role("react", "medium")
    
    print(f"Tech topics: {len(topics.tech)}")
    print(f"Tech-allied topics: {len(topics.tech_allied)}")
    print(f"Behavioral topics: {len(topics.behavioral)}")
    print(f"Archetypes: {len(topics.archetypes)}")
    
    # Show first few tech topics
    print("\nFirst 3 tech topics:")
    for i, topic in enumerate(topics.tech[:3], 1):
        print(f"  {i}. {topic}")


def example_role_derivation():
    """Demonstrate role derivation from various inputs."""
    print("\n=== Role Derivation Example ===")
    
    service = SyllabusService()
    
    test_tracks = [
        "react",
        "frontend developer",
        "javascript",
        "mern stack",
        "node.js",
        "unknown track",
        "",
        None
    ]
    
    for track in test_tracks:
        try:
            role = service._role_manager.derive_role(track)
            print(f"'{track}' -> '{role}'")
        except Exception as e:
            print(f"'{track}' -> ERROR: {e}")


def example_question_ratios():
    """Demonstrate question ratio computation."""
    print("\n=== Question Ratio Example ===")
    
    service = SyllabusService()
    
    scenarios = [
        {"years_experience": None, "has_resume_text": False, "has_skills": False},
        {"years_experience": 0.5, "has_resume_text": False, "has_skills": False},
        {"years_experience": 2.0, "has_resume_text": True, "has_skills": True},
        {"years_experience": 3.0, "has_resume_text": True, "has_skills": False},
        {"years_experience": 5.0, "has_resume_text": False, "has_skills": True},
    ]
    
    for scenario in scenarios:
        ratio = service.compute_question_ratio(**scenario)
        print(f"Scenario {scenario} -> {ratio.tech} tech, {ratio.tech_allied} tech_allied, {ratio.behavioral} behavioral")


def example_resume_extraction():
    """Demonstrate tech skill extraction from resume."""
    print("\n=== Resume Extraction Example ===")
    
    service = SyllabusService()
    
    # Sample resume text
    resume_text = """
    John Doe - Senior React Developer
    
    Experience:
    - 5 years building React applications with TypeScript
    - Expert in Redux, Zustand, and React Query for state management
    - Proficient in Node.js, Express, and MongoDB
    - Experience with Docker, AWS, and CI/CD pipelines
    - Strong knowledge of Jest, Cypress, and testing best practices
    """
    
    # Sample skills list
    skills = ["React", "TypeScript", "Node.js", "MongoDB", "Docker"]
    
    # Extract tech-allied topics
    topics = service.extract_tech_allied_from_resume(
        resume_text=resume_text,
        skills=skills,
        fallback_topics=["Git", "NPM", "Webpack"]
    )
    
    print(f"Extracted {len(topics)} tech-allied topics:")
    for topic in topics:
        print(f"  - {topic}")


def example_caching_performance():
    """Demonstrate caching performance benefits."""
    print("\n=== Caching Performance Example ===")
    
    service = SyllabusService()
    
    # First call - cache miss
    import time
    start_time = time.time()
    topics1 = service.get_topics_for_role("react", "medium")
    first_call_time = time.time() - start_time
    
    # Second call - cache hit
    start_time = time.time()
    topics2 = service.get_topics_for_role("react", "medium")
    second_call_time = time.time() - start_time
    
    print(f"First call (cache miss): {first_call_time:.4f}s")
    print(f"Second call (cache hit): {second_call_time:.4f}s")
    print(f"Speedup: {first_call_time/second_call_time:.1f}x")
    
    # Show cache stats
    stats = service.get_cache_stats()
    print(f"Cache stats: {stats}")


def example_error_handling():
    """Demonstrate error handling and validation."""
    print("\n=== Error Handling Example ===")
    
    service = SyllabusService()
    
    # Test invalid inputs
    test_cases = [
        ("", "medium"),  # Empty role
        ("react", "invalid"),  # Invalid difficulty
        (None, "medium"),  # None role
        ("react", None),  # None difficulty
    ]
    
    for role, difficulty in test_cases:
        try:
            topics = service.get_topics_for_role(role, difficulty)
            print(f"SUCCESS: role='{role}', difficulty='{difficulty}' -> {len(topics.tech)} tech topics")
        except Exception as e:
            print(f"ERROR: role='{role}', difficulty='{difficulty}' -> {e}")


def example_backward_compatibility():
    """Demonstrate backward compatibility with old interface."""
    print("\n=== Backward Compatibility Example ===")
    
    # Import the old-style functions
    from .syllabus import (
        derive_role,
        get_topics_for,
        compute_category_ratio,
        tech_allied_from_resume
    )
    
    # Test old functions still work
    role = derive_role("react")
    print(f"Old derive_role('react') -> '{role}'")
    
    topics = get_topics_for("react", "medium")
    print(f"Old get_topics_for('react', 'medium') -> {len(topics['tech'])} tech topics")
    
    ratio = compute_category_ratio(years_experience=2.0, has_resume_text=True, has_skills=True)
    print(f"Old compute_category_ratio() -> {ratio}")
    
    skills = tech_allied_from_resume("React developer with Node.js experience")
    print(f"Old tech_allied_from_resume() -> {skills}")


def run_all_examples():
    """Run all examples to demonstrate the refactored syllabus service."""
    print("Syllabus Service Refactoring Examples")
    print("=" * 50)
    
    try:
        example_basic_usage()
        example_role_derivation()
        example_question_ratios()
        example_resume_extraction()
        example_caching_performance()
        example_error_handling()
        example_backward_compatibility()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        raise


if __name__ == "__main__":
    run_all_examples()
