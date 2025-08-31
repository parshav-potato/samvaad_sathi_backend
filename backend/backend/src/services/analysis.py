"""Analysis aggregation service for combining multiple analysis types."""

import asyncio
import json
import time
import random
from typing import Dict, List, Any, Tuple
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.manager import settings
from src.models.db.question_attempt import QuestionAttempt
from src.models.schemas.analysis import (
    AggregatedAnalysis, 
    AnalysisMetadata,
    DomainAnalysisResponse,
    CommunicationAnalysisResponse, 
    PaceAnalysisResponse,
    PauseAnalysisResponse
)


class AnalysisAggregationService:
    """Service for aggregating multiple analysis types into a single result."""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://127.0.0.1:8000/api"
        self.timeout = 30.0  # 30 seconds per analysis
        
    async def aggregate_question_analysis(
        self,
        question_attempt_id: int,
        user_id: int,
        analysis_types: List[str],
        auth_token: str,
        db: AsyncSession
    ) -> Tuple[AggregatedAnalysis, AnalysisMetadata, bool, str | None]:
        """
        Aggregate multiple analysis types for a question attempt.
        
        Args:
            question_attempt_id: ID of the question attempt to analyze
            user_id: ID of the user making the request
            analysis_types: List of analysis types to perform
            auth_token: Bearer token for authentication
            db: Database session
            
        Returns:
            Tuple of (aggregated_analysis, metadata, saved_successfully, save_error)
        """
        start_time = time.perf_counter()
        
        # Verify question attempt exists and has transcription
        question_attempt = await self._verify_question_attempt(
            question_attempt_id, user_id, db
        )
        
        if not question_attempt:
            raise ValueError("Question attempt not found or access denied")
            
        if not question_attempt.transcription:
            raise ValueError("Question attempt does not have transcription data")
        
        # Run analyses concurrently
        analysis_results = await self._run_concurrent_analyses(
            question_attempt_id, analysis_types, auth_token
        )
        
        # Aggregate results
        aggregated_analysis = self._build_aggregated_analysis(analysis_results)
        
        # Calculate metadata
        end_time = time.perf_counter()
        total_latency_ms = int((end_time - start_time) * 1000)
        
        completed_analyses = [
            analysis_type for analysis_type, result in analysis_results.items()
            if result.get("success", False)
        ]
        failed_analyses = [
            analysis_type for analysis_type, result in analysis_results.items()
            if not result.get("success", False)
        ]
        
        metadata = AnalysisMetadata(
            total_latency_ms=total_latency_ms,
            completed_analyses=completed_analyses,
            failed_analyses=failed_analyses,
            partial_failure=len(failed_analyses) > 0 and len(completed_analyses) > 0
        )
        
        # Save to database
        saved, save_error = await self._save_analysis_to_db(
            question_attempt, aggregated_analysis, db
        )
        
        return aggregated_analysis, metadata, saved, save_error
    
    async def _verify_question_attempt(
        self, 
        question_attempt_id: int, 
        user_id: int, 
        db: AsyncSession
    ) -> QuestionAttempt | None:
        """Verify question attempt exists and belongs to user."""
        stmt = (
            sqlalchemy.select(QuestionAttempt)
            .join(QuestionAttempt.interview)
            .where(
                QuestionAttempt.id == question_attempt_id,
                QuestionAttempt.interview.has(user_id=user_id)
            )
        )
        query = await db.execute(statement=stmt)
        return query.scalar_one_or_none()
    
    async def _run_concurrent_analyses(
        self, 
        question_attempt_id: int, 
        analysis_types: List[str], 
        auth_token: str
    ) -> Dict[str, Dict[str, Any]]:
        """Run multiple analyses concurrently using direct function calls."""
        
        # Define supported analysis types
        SUPPORTED_ANALYSIS_TYPES = {"domain", "communication", "pace", "pause"}
        
        # Validate and create analysis tasks
        analysis_tasks = []  # List of (analysis_type, task) tuples to avoid overwrites
        analysis_results = {}
        
        for analysis_type in analysis_types:
            if analysis_type not in SUPPORTED_ANALYSIS_TYPES:
                # Immediately record error for unsupported types
                analysis_results[analysis_type] = {
                    "success": False,
                    "error": f"Unsupported analysis type: {analysis_type}. Supported: {SUPPORTED_ANALYSIS_TYPES}",
                    "data": None
                }
            else:
                # Create task with timeout wrapper
                task_coro = self._generate_analysis_result(analysis_type, question_attempt_id)
                timeout_task = asyncio.wait_for(task_coro, timeout=self.timeout)
                analysis_tasks.append((analysis_type, timeout_task))
        
        # Wait for all valid analyses to complete
        if analysis_tasks:
            tasks_only = [task for _, task in analysis_tasks]
            results = await asyncio.gather(*tasks_only, return_exceptions=True)
            
            # Map results back to analysis types
            for i, (analysis_type, _) in enumerate(analysis_tasks):
                result = results[i]
                if isinstance(result, Exception):
                    error_msg = str(result)
                    if isinstance(result, asyncio.TimeoutError):
                        error_msg = f"Analysis timeout after {self.timeout}s"
                    analysis_results[analysis_type] = {
                        "success": False,
                        "error": error_msg,
                        "data": None
                    }
                else:
                    analysis_results[analysis_type] = result
                
        return analysis_results
    
    async def _generate_analysis_result(
        self, 
        analysis_type: str, 
        question_attempt_id: int
    ) -> Dict[str, Any]:
        """Generate analysis result for a specific type."""
        
        try:
            # Simulate some processing time
            await asyncio.sleep(random.uniform(0.1, 0.5))
            
            if analysis_type == "domain":
                data = DomainAnalysisResponse(
                    question_attempt_id=question_attempt_id,
                    domain_score=random.uniform(70.0, 95.0),
                    domain_feedback="Domain knowledge analysis shows good understanding of core concepts.",
                    knowledge_areas=["Core Concepts", "Technical Implementation", "Best Practices"],
                    strengths=["Clear explanations", "Accurate terminology"],
                    improvements=["Could provide more specific examples", "Deeper technical details"]
                ).model_dump()
                
            elif analysis_type == "communication":
                data = CommunicationAnalysisResponse(
                    question_attempt_id=question_attempt_id,
                    communication_score=random.uniform(75.0, 92.0),
                    clarity_score=random.uniform(80.0, 95.0),
                    vocabulary_score=random.uniform(70.0, 90.0),
                    grammar_score=random.uniform(85.0, 98.0),
                    structure_score=random.uniform(75.0, 88.0),
                    communication_feedback="Communication analysis shows clear and structured responses.",
                    recommendations=["Use more varied vocabulary", "Provide clearer examples"]
                ).model_dump()
                
            elif analysis_type == "pace":
                wpm = random.uniform(140.0, 180.0)
                data = PaceAnalysisResponse(
                    question_attempt_id=question_attempt_id,
                    pace_score=random.uniform(70.0, 95.0),
                    words_per_minute=wpm,
                    pace_feedback=f"Speaking pace of {wpm:.1f} WPM is within optimal range.",
                    pace_category="optimal",
                    recommendations=["Maintain current pace", "Consider slight variation for emphasis"]
                ).model_dump()
                
            elif analysis_type == "pause":
                pause_count = random.randint(3, 8)
                avg_pause = random.uniform(0.5, 2.0)
                total_pause = pause_count * avg_pause
                
                data = PauseAnalysisResponse(
                    question_attempt_id=question_attempt_id,
                    pause_score=random.uniform(75.0, 90.0),
                    total_pause_duration=total_pause,
                    pause_count=pause_count,
                    average_pause_duration=avg_pause,
                    longest_pause_duration=random.uniform(1.0, 3.5),
                    pause_feedback="Pause patterns show natural speaking rhythm with appropriate breaks.",
                    recommendations=["Continue natural pausing", "Use strategic pauses for emphasis"]
                ).model_dump()
                
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            return {
                "success": True,
                "error": None,
                "data": data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating {analysis_type} analysis: {str(e)}",
                "data": None
            }
    
    def _build_aggregated_analysis(
        self, 
        analysis_results: Dict[str, Dict[str, Any]]
    ) -> AggregatedAnalysis:
        """Build aggregated analysis from individual results."""
        
        # Get valid field names from the AggregatedAnalysis model
        valid_fields = set(AggregatedAnalysis.model_fields.keys())
        
        # Build payload dict with only valid model fields
        payload = {}
        for analysis_type, result in analysis_results.items():
            if analysis_type in valid_fields:
                if result.get("success", False) and result.get("data"):
                    payload[analysis_type] = result["data"]
                else:
                    payload[analysis_type] = None
        
        # Construct and validate AggregatedAnalysis instance
        return AggregatedAnalysis(**payload)
    
    async def _save_analysis_to_db(
        self,
        question_attempt: QuestionAttempt,
        aggregated_analysis: AggregatedAnalysis,
        db: AsyncSession
    ) -> Tuple[bool, str | None]:
        """Save aggregated analysis to database."""
        try:
            # Convert Pydantic model to dict for JSON storage
            analysis_dict = aggregated_analysis.model_dump(exclude_none=True)
            
            # Update the question attempt using SQL update to avoid session issues
            stmt = (
                sqlalchemy.update(QuestionAttempt)
                .where(QuestionAttempt.id == question_attempt.id)
                .values(analysis_json=analysis_dict)
            )
            await db.execute(stmt)
            await db.commit()
            
            return True, None
            
        except Exception as e:
            await db.rollback()
            return False, str(e)


# Create service instance
analysis_service = AnalysisAggregationService()
