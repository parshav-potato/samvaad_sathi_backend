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
        timeout=float(getattr(settings, "OPENAI_TIMEOUT_SECONDS", 60.0)),
        max_retries=3,
    )
    return _client


class ResumeEntitiesLLM(pydantic.BaseModel):
    skills: list[str] = pydantic.Field(default_factory=list)
    years_experience: float | None = None


class EducationItemLLM(pydantic.BaseModel):
    degree: str | None = None
    institution: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ExperienceItemLLM(pydantic.BaseModel):
    company: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsibilities: list[str] | None = None
    technologies: list[str] | None = None


class ProjectItemLLM(pydantic.BaseModel):
    name: str | None = None
    description: str | None = None
    technologies: list[str] | None = None
    link: str | None = None


class ResumeEntitiesV2LLM(pydantic.BaseModel):
    # Backward-compatible core
    skills: list[str] = pydantic.Field(default_factory=list)
    years_experience: float | None = None
    # Additional details
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    links: list[str] | None = None
    summary: str | None = None
    education: list[EducationItemLLM] | None = None
    experience: list[ExperienceItemLLM] | None = None
    projects: list[ProjectItemLLM] | None = None
    certifications: list[str] | None = None
    languages: list[str] | None = None
    job_titles: list[str] | None = None
    companies: list[str] | None = None


class QuestionsItemLLM(pydantic.BaseModel):
    text: str
    topic: str | None = None
    difficulty: str | None = None
    category: str | None = None  # tech | tech_allied | behavioral


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
        # Use Chat Completions for all models; switch token param for newer families
        raw = "{}"
        is_new_family = any(str(model).lower().startswith(p) for p in ("gpt-5", "gpt-4.1", "o4", "o3"))
        token_param_key = "max_completion_tokens" if is_new_family else "max_tokens"
        kwargs = {
            "model": model,
            "response_format": {"type": "json_object"},
            token_param_key: 2048,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content if isinstance(user_content, str) else json.dumps(user_content, ensure_ascii=False)},
            ],
        }
        # Only include temperature for older models; new families accept only the default
        if not is_new_family:
            kwargs["temperature"] = temperature
        resp = await client.chat.completions.create(**kwargs)
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


async def extract_resume_entities_v2_with_llm(text: str) -> tuple[dict[str, Any], str | None, int | None, str]:
    """Extended resume extraction including education, experience, projects, and contact info.

    Returns (data_dict, error, latency_ms, model). On missing API key or empty text, returns empty dict and no error.
    """
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key or not text:
        return {}, None, None, model

    sys_prompt = (
        "Extract structured resume details from the provided text. "
        "Return ONLY valid JSON matching this schema: {\n"
        "  skills: string[],\n"
        "  years_experience: number|null,\n"
        "  full_name: string|null, email: string|null, phone: string|null, location: string|null,\n"
        "  links: string[]|null, summary: string|null,\n"
        "  education: [{ degree?: string, institution?: string, start_date?: string, end_date?: string }] | null,\n"
        "  experience: [{ company?: string, role?: string, start_date?: string, end_date?: string, responsibilities?: string[], technologies?: string[] }] | null,\n"
        "  projects: [{ name?: string, description?: string, technologies?: string[], link?: string }] | null,\n"
        "  certifications: string[]|null, languages: string[]|null, job_titles: string[]|null, companies: string[]|null\n"
        "}. Dates should be simple strings (e.g., 'Jan 2021' or '2021-01'). Do not include markdown."
    )
    input_text = text[:20000]

    try:
        result, error, latency_ms, model = await structured_output(
            ResumeEntitiesV2LLM,
            system_prompt=sys_prompt,
            user_content=input_text,
            temperature=0,
        )
        data: dict[str, Any] = result.model_dump() if result else {}
        return data, error, latency_ms, model
    except Exception as e:  # noqa: BLE001
        # Fallback to minimal response on error
        latency_ms = None
        return {}, str(e), latency_ms, model


async def generate_interview_questions_with_llm(
    track: str,
    context_text: str | None = None,
    count: int = 3,
    difficulty: str | None = None,
    *,
    syllabus_topics: dict[str, list[str]] | None = None,
    ratio: dict[str, int] | None = None,
    influence: dict[str, Any] | None = None,
) -> tuple[list[str], str | None, int | None, str, list[dict[str, Any]] | None]:
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
        "You are an expert interviewer. Generate concise, specific interview questions for a software candidate. "
        "Avoid open-ended prompts; ask targeted questions that require concrete answers. "
        "Return ONLY valid JSON with keys: 'questions' (string[]) AND 'items' (array of objects with fields: text, topic, difficulty, category)."
        "Understand that this is a verbal interview setting, so questions should be suitable for spoken responses."
    )
    user_prompt = {
        "track": track,
        "count": max(1, min(10, int(count or 3))),
        "context": (context_text or "")[:4000],
        "difficulty": (difficulty or "medium"),
        # Category mix and topics per product requirements
        "categories": {
            "definitions": {
                "tech": "Core technical questions for the target role",
                "tech_allied": "Technical questions allied to the candidate's background/experience",
                "behavioral": "Behavioral questions from the provided list",
            },
            "ratio": ratio or {"tech": 2, "tech_allied": 2, "behavioral": 1},
        },
        "syllabus": syllabus_topics or {},
        "archetypes": (syllabus_topics or {}).get("archetypes", []),
        "depth_guidelines": (syllabus_topics or {}).get("depth_guidelines", []),
        "behavioral_topics": (syllabus_topics or {}).get("behavioral", []),
        "influence": influence or {},
        "constraints": [
            "No preambles, no numbering in the JSON itself",
            "Questions should be single sentences when possible",
            "Avoid duplicate or trivial questions",
            "Each item must include a 'category' of tech | tech_allied | behavioral",
            "Behavioral questions must come from the provided behavioral topics and probe for specific actions/decisions",
            "Tech-allied questions should be related to the candidate's experience/skills when available",
            "Vary topics and ensure depth appropriate to difficulty; do not ask purely opinion-based questions",
            "Use a mix of the provided archetypes to ensure variety (e.g., concept, trade-offs, debug, design)",
            "Follow the depth guidelines for the given difficulty",
            "Ask deep questions but make sure they have a clear, specific answer"
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
                    {"text": it.text.strip(), "topic": it.topic, "difficulty": it.difficulty, "category": it.category}
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

