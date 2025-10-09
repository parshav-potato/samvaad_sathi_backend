import json
import random
import time
from typing import Any, Type, List, Dict

import pydantic
from openai import AsyncOpenAI
from src.config.manager import settings
from src.models.schemas.summary_report import SummarySection, SummarySectionGroup, SummaryMetrics

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


# Base class for items with date ranges
class BaseDateRangeItemLLM(pydantic.BaseModel):
    """Base class for items with start/end dates."""
    start_date: str | None = None
    end_date: str | None = None


class EducationItemLLM(BaseDateRangeItemLLM):
    """Education item with degree and institution."""
    degree: str | None = None
    institution: str | None = None


class ExperienceItemLLM(BaseDateRangeItemLLM):
    """Experience item with company, role, and related data."""
    company: str | None = None
    role: str | None = None
    responsibilities: list[str] | None = None
    technologies: list[str] | None = None


class ProjectItemLLM(pydantic.BaseModel):
    """Project item with name, description, and technologies."""
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
    llm_schema: str | None = None


class LLMKnowledgeBreakdownStrict(pydantic.BaseModel):
    accuracy: float = pydantic.Field(..., ge=0.0, le=5.0)
    depth: float = pydantic.Field(..., ge=0.0, le=5.0)
    coverage: float = pydantic.Field(..., ge=0.0, le=5.0)
    relevance: float = pydantic.Field(..., ge=0.0, le=5.0)


class LLMSpeechBreakdownStrict(pydantic.BaseModel):
    pacing: float = pydantic.Field(..., ge=0.0, le=5.0)
    structure: float = pydantic.Field(..., ge=0.0, le=5.0)
    pauses: float = pydantic.Field(..., ge=0.0, le=5.0)
    grammar: float = pydantic.Field(..., ge=0.0, le=5.0)


class LLMKnowledgeCompetenceStrict(pydantic.BaseModel):
    average5pt: float = pydantic.Field(..., ge=0.0, le=5.0)
    averagePct: float = pydantic.Field(..., ge=0.0, le=100.0)
    breakdown: LLMKnowledgeBreakdownStrict


class LLMSpeechStructureStrict(pydantic.BaseModel):
    average5pt: float = pydantic.Field(..., ge=0.0, le=5.0)
    averagePct: float = pydantic.Field(..., ge=0.0, le=100.0)
    breakdown: LLMSpeechBreakdownStrict


class LLMOverallScoreSummaryStrict(pydantic.BaseModel):
    knowledgeCompetence: LLMKnowledgeCompetenceStrict
    speechStructure: LLMSpeechStructureStrict


class LLMSectionGroupStrict(pydantic.BaseModel):
    label: str
    items: list[str] = pydantic.Field(default_factory=list)


class LLMSectionStrict(pydantic.BaseModel):
    heading: str
    subtitle: str | None = None
    groups: list[LLMSectionGroupStrict] = pydantic.Field(default_factory=list)


class LLMPerQuestionItemStrict(pydantic.BaseModel):
    questionAttemptId: int
    questionText: str | None = None
    keyTakeaways: list[str] = pydantic.Field(default_factory=list)
    knowledgeScorePct: float = pydantic.Field(..., ge=0.0, le=100.0)
    speechScorePct: float = pydantic.Field(..., ge=0.0, le=100.0)


class LLMTopicHighlightsStrict(pydantic.BaseModel):
    strengthsTopics: list[str] = pydantic.Field(default_factory=list)
    improvementTopics: list[str] = pydantic.Field(default_factory=list)


class StrictSummarySynthesisLLM(pydantic.BaseModel):
    """Strict, non-optional output for UI-style summary synthesis (no metadata)."""
    metrics: LLMOverallScoreSummaryStrict
    strengths: LLMSectionStrict
    areasOfImprovement: LLMSectionStrict
    actionableInsights: LLMSectionStrict
    perQuestion: list[LLMPerQuestionItemStrict] | None = None
    topicHighlights: LLMTopicHighlightsStrict | None = None


async def synthesize_summary_sections(
    *,
    per_question_inputs: List[dict],
    computed_metrics: Dict[str, Any],
    max_questions: int | None = None,
) -> tuple[dict, str | None, int | None, str]:
    """
    Drive the LLM to create the three sections from complete per-question analyses.
    Returns: (summary_json, error, latency_ms, model)
    """
    model = settings.OPENAI_MODEL
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        # No key: return empty structures; caller can fallback to heuristic
        return {"metrics": {}, "strengths": {}, "areasOfImprovement": {}, "actionableInsights": {}}, None, None, model

    if max_questions is not None:
        per_question_inputs = per_question_inputs[:max_questions]

    sys_prompt = (
        "You are an expert technical interview coach. Given per-question analyses (domain, communication, pace, "
        "pause) for up to 5 questions with scores and suggestions, synthesize a concise report with the exact JSON "
        "shape below. Use measured data to compute averages and select concrete strengths and prioritized "
        "improvements. Keep tone constructive and actionable. Return ONLY valid JSON (no markdown). Do NOT output nulls anywhere.\n\n"
        "Strict JSON schema and constraints (no nulls): {\n"
        "  metrics: {\n"
        "    knowledgeCompetence: { average5pt:number(0..5), averagePct:number(0..100), breakdown:{accuracy:number(0..5), depth:number(0..5), coverage:number(0..5), relevance:number(0..5)} },\n"
        "    speechStructure: { average5pt:number(0..5), averagePct:number(0..100), breakdown:{pacing:number(0..5), structure:number(0..5), pauses:number(0..5), grammar:number(0..5)} }\n"
        "  },\n"
        "  strengths: { heading:string, subtitle?:string, groups:[{ label:string, items:string[] }] },\n"
        "  areasOfImprovement: { heading:string, subtitle?:string, groups:[{ label:string, items:string[] }] },\n"
        "  actionableInsights: { heading:string, subtitle?:string, groups:[{ label:string, items:string[] }] },\n"
        "  perQuestion?: [{ questionAttemptId:number, questionText?:string, keyTakeaways:string[], knowledgeScorePct:number(0..100), speechScorePct:number(0..100) }],\n"
        "  topicHighlights?: { strengthsTopics:string[], improvementTopics:string[] }\n"
        "}\n\n"
        "Use the provided computed_metrics directly for knowledgeCompetence: averagePct equals computed kc_avg_pct, "
        "average5pt equals kc_avg_pct/20, and breakdown items equal kc_breakdown_pct items/20 rounded to two decimals. "
        "Do not invent numbers for knowledgeCompetence; derive exactly from computed_metrics."
    )

    user_content = {
        "per_question": per_question_inputs,
        "computed_metrics": computed_metrics,
        "guidelines": [
            "Base averages on provided metrics; do not invent numbers",
            "Summaries must reflect specific issues observed in analyses",
            "Actionable steps should be concrete and phrased as imperatives",
            "Avoid highly technical jargon like WPM or words per minute, Keep everything simple and easy to understand",
            "When suggesting improvements, connect them to specific weaknesses observed"
        ],
    }

    result, error, latency_ms, model = await structured_output(
        StrictSummarySynthesisLLM,
        system_prompt=sys_prompt,
        user_content=user_content,
        temperature=0,
    )

    data: dict = {}
    if result:
        data = result.model_dump()
    return data, error, latency_ms, model

# Base classes for common patterns
class BaseAnalysisLLM(pydantic.BaseModel):
    """Base class for analysis responses with common fields."""
    overall_score: float | None = None
    criteria: dict[str, Any] | None = None
    summary: str | None = None
    strengths: list[str] | None = None
    improvements: list[str] | None = None
    suggestions: list[str] | None = None  # Deprecated, use improvements
    confidence: float | None = None


class BaseItemLLM(pydantic.BaseModel):
    """Base class for item responses with common fields."""
    text: str
    topic: str | None = None
    difficulty: str | None = None


class QuestionsItemLLM(BaseItemLLM):
    """Question item with category field."""
    category: str | None = None  # tech | tech_allied | behavioral


class QuestionsResponseLLM(pydantic.BaseModel):
    """Response containing structured question items."""
    items: list[QuestionsItemLLM] = pydantic.Field(default_factory=list)


class DomainAnalysisLLM(BaseAnalysisLLM):
    """Domain knowledge analysis with specific fields."""
    misconceptions: dict[str, Any] | None = None
    examples: dict[str, Any] | None = None


class CommunicationAnalysisLLM(BaseAnalysisLLM):
    """Communication analysis with specific fields."""
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
        "You are an expert interviewer. Generate concise, specific interview questions for a candidate. "
        "Avoid open-ended prompts; ask targeted questions that require concrete answers, but keep in mind to ask deep questions that will take time to answer NOT one sentence or one word answers"
        "Return ONLY valid JSON with key: 'items' (array of objects with fields: text, topic, difficulty, category)."
        "Understand that this is a verbal interview setting, so questions should STRICTLY be suitable for strictly spoken responses."
    )
    # Prepare a sampled syllabus so we don't send the entire topic bank to the LLM
    topics = syllabus_topics or {}
    r = ratio or {"tech": 2, "tech_allied": 2, "behavioral": 1}
    total = max(1, min(10, int(count or 3)))
    # Normalize ratio to total questions (we use it only as guidance for sampling size)
    r_tech = max(0, int(r.get("tech", 0)))
    r_allied = max(0, int(r.get("tech_allied", 0)))
    r_beh = max(0, int(r.get("behavioral", 0)))

    def _pick(ls: list[str] | None, n: int) -> list[str]:
        pool = list(ls or [])
        if not pool:
            return []
        k = min(len(pool), max(1, n))
        # random.sample requires k <= len(pool)
        return random.sample(pool, k)

    # Heuristic: provide up to 2x topics per expected question in that category (min 3)
    tech_pool = _pick(topics.get("tech"), max(2, r_tech * 2))
    allied_pool = _pick(topics.get("tech_allied"), max(2, r_allied * 2))
    beh_pool_full = list(topics.get("behavioral", []))
    beh_pool = _pick(beh_pool_full, max(3, r_beh * 2 if r_beh > 0 else 3))

    sampled_syllabus = {
        "tech": tech_pool,
        "tech_allied": allied_pool,
        # Keep behavioral also as part of syllabus for uniformity; LLM will still honor categories
        "behavioral": beh_pool,
    }

    user_prompt = {
        "track": track,
        "count": total,
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
        # Only pass a random subset of topics so the model focuses and varies questions over runs
        "syllabus": sampled_syllabus,
        "archetypes": (syllabus_topics or {}).get("archetypes", []),
        "depth_guidelines": (syllabus_topics or {}).get("depth_guidelines", []),
        # Also trim behavioral list passed separately to reinforce selection
        "behavioral_topics": beh_pool,
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
            # Extract questions from items and create structured items
            if result.items:
                questions = [it.text.strip() for it in result.items]
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
        "examples (present: bool, notes: string[])), summary (string), strengths (string[] of positive aspects), "
        "improvements (string[] of areas to improve), confidence (0-1). "
        "IMPORTANT: Always include both strengths and improvements arrays, even if scores are low. "
        "Strengths should highlight what the candidate did well, even if partial. "
        "Improvements should provide actionable feedback for growth."
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
        "tone_empathy (score:number, notes:string[])), summary (string), strengths (string[] of positive aspects), "
        "improvements (string[] of areas to improve), suggestions (string[] for backward compatibility), confidence (0-1). "
        "Always include both strengths and improvements arrays, even if scores are low. "
        "Strengths should highlight what the candidate did well. Improvements should identify specific areas to work on. "
        "Heavily penalize short answers that dont have enough nuance and detail"
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

