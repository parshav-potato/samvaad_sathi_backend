import json
import time
from typing import Any, Type

import pydantic
from openai import AsyncOpenAI
from src.config.manager import settings

# Lazy client holder; create only when needed and when API key is present
_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI | None:
    global _client
    if _client is not None:
        return _client
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    _client = AsyncOpenAI(
        api_key=api_key,
        timeout=30.0,
        max_retries=3,
    )
    return _client


class ResumeEntitiesLLM(pydantic.BaseModel):
    skills: list[str] = pydantic.Field(default_factory=list)
    years_experience: float | None = None


class QuestionsItemLLM(pydantic.BaseModel):
    text: str
    topic: str | None = None
    difficulty: str | None = None


class QuestionsResponseLLM(pydantic.BaseModel):
    questions: list[str] = pydantic.Field(default_factory=list)
    items: list[QuestionsItemLLM] | None = None


class DomainAnalysisLLM(pydantic.BaseModel):
    overall_score: float | None = None
    criteria: dict[str, Any] | None = None
    summary: str | None = None
    suggestions: list[str] | None = None
    confidence: float | None = None
    misconceptions: dict[str, Any] | None = None
    examples: dict[str, Any] | None = None


class CommunicationAnalysisLLM(pydantic.BaseModel):
    overall_score: float | None = None
    criteria: dict[str, Any] | None = None
    summary: str | None = None
    suggestions: list[str] | None = None
    confidence: float | None = None
    jargon_use: dict[str, Any] | None = None
    tone_empathy: dict[str, Any] | None = None


class PausesSuggestionLLM(pydantic.BaseModel):
    modified_transcript: str


class PauseCoachLLM(pydantic.BaseModel):
    actionable_feedback: str
    score: int


async def structured_output(
    model_class: Type[pydantic.BaseModel],
    *,
    system_prompt: str,
    user_content: Any,
    temperature: float = 0,
) -> tuple[pydantic.BaseModel | None, str | None, int | None, str]:
    """Call OpenAI asynchronously with JSON response_format and validate against Pydantic model."""
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None, None, None, model

    start = time.perf_counter()
    try:
        client = _get_client()
        if client is None:
            return None, None, None, model
        resp = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content if isinstance(user_content, str) else json.dumps(user_content, ensure_ascii=False)},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        parsed = model_class.model_validate(data)
        latency_ms = int((time.perf_counter() - start) * 1000)
        return parsed, None, latency_ms, model
    except Exception as e:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - start) * 1000)
        return None, str(e), latency_ms, model


async def extract_resume_entities_with_llm(text: str) -> tuple[list[str], float | None, str | None, int | None, str]:
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key or not text:
        return [], None, None, None, model

    start = time.perf_counter()
    error: str | None = None
    skills: list[str] = []
    years: float | None = None

    system_prompt = (
        "Extract skills and years of professional experience from the resume text. "
        "Return ONLY a valid JSON object with exactly these keys: "
        '{"skills": ["skill1", "skill2", ...], "years_experience": number_or_null}. '
        "Do not include any markdown formatting, explanations, or other text. "
        "For skills, extract technical skills, programming languages, tools, and frameworks. "
        "For years_experience, calculate total professional work experience as a number."
    )
    input_text = text[:20000]

    try:
        result, perr, latency, model = await structured_output(
            ResumeEntitiesLLM,
            system_prompt=system_prompt,
            user_content=input_text,
            temperature=0,
        )
        error = perr
        if result:
            skills = [str(x) for x in result.skills]
            years = result.years_experience
        latency_ms = latency
    except Exception as e:
        error = str(e)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return skills, years, error, latency_ms, model


async def generate_interview_questions_with_llm(track: str, context_text: str | None = None, count: int = 3, difficulty: str | None = None) -> tuple[list[str], str | None, int | None, str, list[dict[str, Any]] | None]:
    """
    Generate interview questions using an LLM given a track and optional context (e.g., resume_text).
    Returns (questions, error, latency_ms, model). On missing API key, returns empty questions and no error.
    """
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return [], None, None, model, None

    start = time.perf_counter()
    error: str | None = None
    questions: list[str] = []
    structured_items: list[dict[str, Any]] | None = None

    sys_prompt = (
        "You are an expert interviewer. Generate concise, clear interview questions tailored to the track. "
        "Return ONLY valid JSON with keys: 'questions' (string[]) AND 'items' (array of objects with fields: text, topic, difficulty)."
    )
    user_prompt = {
        "track": track,
        "count": max(1, min(10, int(count or 3))),
        "context": (context_text or "")[:4000],
        "difficulty": (difficulty or "medium"),
        "constraints": [
            "No preambles, no numbering in the JSON itself",
            "Questions should be single sentences when possible",
            "Avoid duplicate or trivial questions",
        ],
    }

    try:
        result, perr, latency, model = await structured_output(
            QuestionsResponseLLM,
            system_prompt=sys_prompt,
            user_content=user_prompt,
            temperature=0.2,
        )
        error = perr
        if result:
            questions = [str(x).strip() for x in (result.questions or [])]
            if result.items is not None:
                structured_items = [
                    {"text": it.text.strip(), "topic": it.topic, "difficulty": it.difficulty}
                    for it in result.items
                ]
        latency_ms = latency
    except Exception as e:
        error = str(e)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return questions, error, latency_ms, model, structured_items


async def analyze_domain_with_llm(
    *,
    user_profile: dict[str, Any],
    question_text: str | None,
    transcription: str,
) -> tuple[dict[str, Any], str | None, int | None, str]:
    """
    Perform domain knowledge analysis using LLM. Returns (analysis_json, error, latency_ms, model).
    Never raises; on missing API key returns empty analysis and no error.
    """
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return {}, None, None, model

    start = time.perf_counter()
    error: str | None = None
    analysis: dict[str, Any] = {}

    sys_prompt = (
        "You are a strict technical interviewer. Assess the candidate's domain knowledge based on the transcript. "
        "Return ONLY valid JSON with keys: overall_score (0-100), criteria (object with correctness/depth/coverage/"
        "relevance each having score (0-100) and reasons (string[]), misconceptions (present: bool, notes: string[]), "
        "examples (present: bool, notes: string[])), summary (string), suggestions (string[]), confidence (0-1)."
    )
    user_content = {
        "user_profile": {k: v for k, v in user_profile.items() if v is not None},
        "question": question_text or "",
        "transcription": (transcription or "")[:8000],
    }

    def _clean_and_parse_json(raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        # Strip common code fences
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            # Best-effort extraction of first JSON object/array
            start_obj = text.find('{')
            start_arr = text.find('[')
            start = min(x for x in [start_obj, start_arr] if x != -1) if (start_obj != -1 or start_arr != -1) else -1
            end_obj = text.rfind('}')
            end_arr = text.rfind(']')
            end = max(end_obj, end_arr)
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1]
                # Remove trailing commas before closing braces/brackets
                import re as _re
                candidate = _re.sub(r',\s*(\}|\])', r'\1', candidate)
                return json.loads(candidate)
            raise ValueError("LLM response did not contain valid JSON")

    result, error, latency_ms, model = await structured_output(
        DomainAnalysisLLM,
        system_prompt=sys_prompt,
        user_content=user_content,
        temperature=0,
    )

    analysis: dict[str, Any] = {}
    if result:
        analysis = result.model_dump()
    return analysis, error, latency_ms, model


async def analyze_communication_with_llm(
    *,
    user_profile: dict[str, Any],
    question_text: str | None,
    transcription: str,
    aux_metrics: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str | None, int | None, str]:
    """
    Perform communication analysis using LLM. Returns (analysis_json, error, latency_ms, model).
    Never raises; on missing API key returns empty analysis and no error.
    """
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return {}, None, None, model

    start = time.perf_counter()
    error: str | None = None
    analysis: dict[str, Any] = {}

    sys_prompt = (
        "You are a communication coach. Assess clarity, structure, coherence, conciseness, jargon use, and tone/empathy. "
        "Return ONLY valid JSON with keys: overall_score (0-100), criteria (object with clarity/structure/coherence/"
        "conciseness each having score (0-100) and reasons (string[]), jargon_use (score:number, notes:string[]), "
        "tone_empathy (score:number, notes:string[])), summary (string), suggestions (string[]), confidence (0-1)."
    )
    payload = {
        "user_profile": {k: v for k, v in user_profile.items() if v is not None},
        "question": question_text or "",
        "transcription": (transcription or "")[:8000],
        "aux_metrics": aux_metrics or {},
    }

    def _clean_and_parse_json(raw_text: str) -> dict[str, Any]:
        text = (raw_text or "").strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            start_obj = text.find('{')
            start_arr = text.find('[')
            start = min(x for x in [start_obj, start_arr] if x != -1) if (start_obj != -1 or start_arr != -1) else -1
            end_obj = text.rfind('}')
            end_arr = text.rfind(']')
            end = max(end_obj, end_arr)
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1]
                import re as _re
                candidate = _re.sub(r',\s*(\}|\])', r'\1', candidate)
                return json.loads(candidate)
            raise ValueError("LLM response did not contain valid JSON")

    result, error, latency_ms, model = await structured_output(
        CommunicationAnalysisLLM,
        system_prompt=sys_prompt,
        user_content=payload,
        temperature=0,
    )

    analysis: dict[str, Any] = {}
    if result:
        analysis = result.model_dump()
    return analysis, error, latency_ms, model

