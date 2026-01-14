"""Service for analyzing structure practice answers using LLM."""

import logging
from pydantic import BaseModel, Field
from src.services.llm import structured_output

logger = logging.getLogger(__name__)


class FrameworkSectionAnalysis(BaseModel):
    """Analysis for a single framework section."""
    name: str
    present: bool
    quality: str  # "good", "partial", "missing"
    time_estimate_seconds: int = Field(..., ge=0, le=300)


class StructureAnalysisResult(BaseModel):
    """Structured LLM output for structure analysis."""
    framework_detected: str  # e.g., "C-T-E-T-D", "STAR", "Custom"
    sections: list[FrameworkSectionAnalysis]
    completion_percentage: int = Field(..., ge=0, le=100)
    key_insight: str
    progress_message: str


async def analyze_structure_answer(
    *,
    question_text: str,
    structure_hint: str,
    answer_text: str,
) -> tuple[StructureAnalysisResult | None, str | None, int, str | None]:
    """
    Analyze a structure practice answer using LLM.
    
    Args:
        question_text: The question being answered
        structure_hint: The structure hint provided to the user
        answer_text: The user's answer to analyze
    
    Returns:
        Tuple of (analysis_result, error_message, latency_ms, llm_model)
    """
    # Determine framework from hint
    framework = "C-T-E-T-D"  # Default
    if "STAR" in structure_hint.upper():
        framework = "STAR"
    elif "C-T-E-T-D" in structure_hint.upper():
        framework = "C-T-E-T-D"
    
    # Build analysis prompt
    system_prompt = f"""You are an expert interview coach analyzing structured answers.
Analyze the answer based on the {framework} framework.

For C-T-E-T-D:
- Context: Background and setup
- Theory: Conceptual explanation
- Example: Concrete example with details
- Trade-offs: Pros/cons or alternatives
- Decision: Conclusion or recommendation

For STAR:
- Situation: Context and background
- Task: What needed to be done
- Action: Steps taken
- Result: Outcome and impact

Analyze if each section is:
- "good": Well-developed, clear, specific
- "partial": Present but underdeveloped or rushed
- "missing": Not addressed

Estimate time spent on each section (in seconds, max 300 per section) based on depth and detail.
Provide a key insight about what the candidate should improve.
Calculate completion percentage (0-100) based on sections present and their quality.

Return ONLY valid JSON matching this structure:
{{
  "framework_detected": "C-T-E-T-D" or "STAR",
  "sections": [
    {{
      "name": "section name",
      "present": true/false,
      "quality": "good"/"partial"/"missing",
      "time_estimate_seconds": integer (0-300)
    }}
  ],
  "completion_percentage": integer (0-100),
  "key_insight": "detailed insight string",
  "progress_message": "encouraging message based on completion"
}}"""

    user_content = {
        "question": question_text,
        "structure_hint": structure_hint,
        "answer": answer_text,
        "framework": framework,
        "instructions": [
            f"Analyze based on {framework} framework sections",
            "Assess each section for presence and quality",
            "Estimate realistic time spent per section (max 300s each)",
            "Calculate overall completion percentage",
            "Provide specific, actionable insight based on what's missing"
        ]
    }

    # Use structured_output helper from llm.py
    result, error, latency_ms, model = await structured_output(
        StructureAnalysisResult,
        system_prompt=system_prompt,
        user_content=user_content,
        temperature=0.3,
    )
    
    if result:
        logger.info(f"Structure analysis completed: {framework}, completion={result.completion_percentage}%, latency={latency_ms}ms")
    
    return result, error, latency_ms, model


def _estimate_section_time(answer_text: str, section_text: str) -> int:
    """
    Estimate time spent on a section based on word count and complexity.
    Simple heuristic: ~30 words per minute for thoughtful writing.
    """
    if not section_text:
        return 0
    
    word_count = len(section_text.split())
    # Assume 30 words/minute = 0.5 words/second = 2 seconds/word
    estimated_seconds = int(word_count * 2)
    
    # Cap at reasonable limits
    return min(max(estimated_seconds, 5), 120)
