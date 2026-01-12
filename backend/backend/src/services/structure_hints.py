"""Service for generating structure hints for interview questions."""

import json
import logging
import time
from typing import Any

from openai import AsyncOpenAI
from src.config.manager import settings

logger = logging.getLogger(__name__)

# Lazy client holder
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI | None:
    """Get or create OpenAI client."""
    global _client
    if _client is not None:
        return _client
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    _client = AsyncOpenAI(
        api_key=api_key,
        timeout=float(getattr(settings, "OPENAI_TIMEOUT_SECONDS", 60.0)),
        max_retries=3,
    )
    return _client


async def generate_structure_hints_for_questions(
    questions: list[dict[str, Any]],
    track: str,
    difficulty: str,
) -> tuple[dict[str, str], str | None, int, str]:
    """
    Generate structure hints for interview questions.
    
    Args:
        questions: List of question dicts with 'text', 'topic', 'category' keys
        track: Interview track (e.g., 'data_science', 'frontend')
        difficulty: Interview difficulty level
    
    Returns:
        Tuple of (hints_map, error, latency_ms, model):
        - hints_map: Dict mapping question text to structure hint
        - error: Error message if failed, None if successful
        - latency_ms: Time taken for LLM call
        - model: Model name used
    """
    client = _get_client()
    if not client:
        logger.warning("OpenAI client not available, returning fallback hints")
        return _generate_fallback_hints(questions), None, 0, "fallback"
    
    if not questions:
        return {}, None, 0, "none"
    
    # Build the prompt
    questions_list = []
    for i, q in enumerate(questions, 1):
        text = q.get("text", "")
        topic = q.get("topic", "")
        category = q.get("category", "technical")
        questions_list.append(f"{i}. {text} [Topic: {topic}, Category: {category}]")
    
    questions_text = "\n".join(questions_list)
    
    system_prompt = """You are an expert interview coach helping candidates prepare for technical interviews.
Your task is to provide brief structure hints (1-2 lines) that guide candidates on how to structure their answers effectively.

The hints should:
- Focus on answer structure, NOT content
- Be concise (max 2 lines)
- Help candidates organize their thoughts
- Suggest frameworks or approaches (e.g., STAR method, problem-solution-result, etc.)
- NOT give away the answer

Examples:
- "Start with the problem context, explain your approach step-by-step, then discuss the outcome and what you learned."
- "Use the STAR method: describe the Situation, your Task, Actions taken, and Results achieved."
- "Break down into: definition, use cases, pros/cons, and when you'd recommend it."
"""

    user_prompt = f"""Interview Track: {track}
Difficulty: {difficulty}

Questions:
{questions_text}

For each question above, provide a structure hint in the following JSON format:
{{
    "hints": [
        {{"question_number": 1, "hint": "Your structure hint here"}},
        {{"question_number": 2, "hint": "Your structure hint here"}},
        ...
    ]
}}

Return ONLY the JSON, no additional text."""

    start_time = time.time()
    error = None
    model_name = settings.OPENAI_MODEL or "gpt-4o-mini"
    
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        if not response.choices:
            logger.warning("No choices in OpenAI response for structure hints")
            return _generate_fallback_hints(questions), "No response from LLM", latency_ms, model_name
        
        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty content in OpenAI response for structure hints")
            return _generate_fallback_hints(questions), "Empty response from LLM", latency_ms, model_name
        
        # Parse JSON response
        try:
            # Clean up potential markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed = json.loads(content)
            hints_list = parsed.get("hints", [])
            
            # Map hints to questions
            hints_map = {}
            for i, q in enumerate(questions, 1):
                hint_obj = next((h for h in hints_list if h.get("question_number") == i), None)
                if hint_obj:
                    hints_map[q.get("text", "")] = hint_obj.get("hint", _get_fallback_hint_for_question(q))
                else:
                    hints_map[q.get("text", "")] = _get_fallback_hint_for_question(q)
            
            return hints_map, None, latency_ms, model_name
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response for structure hints: {e}")
            return _generate_fallback_hints(questions), f"JSON parse error: {str(e)}", latency_ms, model_name
    
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error generating structure hints with LLM: {e}")
        return _generate_fallback_hints(questions), str(e), latency_ms, model_name


def _generate_fallback_hints(questions: list[dict[str, Any]]) -> dict[str, str]:
    """Generate fallback hints when LLM is unavailable."""
    hints_map = {}
    for q in questions:
        hints_map[q.get("text", "")] = _get_fallback_hint_for_question(q)
    return hints_map


def _get_fallback_hint_for_question(question: dict[str, Any]) -> str:
    """Generate a fallback hint for a single question based on category."""
    category = (question.get("category") or "technical").lower()
    
    if "behavioral" in category:
        return "Use STAR method: Situation, Task, Action, Result. Focus on your specific role and measurable outcomes."
    elif "system" in category or "design" in category:
        return "Start with requirements and constraints, then present your high-level architecture before diving into components and trade-offs."
    elif "algorithm" in category or "coding" in category:
        return "Clarify assumptions, explain your approach, walk through an example, then discuss time/space complexity and edge cases."
    else:
        return "Begin with context and definition, explain your reasoning step-by-step, then summarize key takeaways and practical applications."
