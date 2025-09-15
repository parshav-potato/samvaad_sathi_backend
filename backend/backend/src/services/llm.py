import json
import os
import time
from typing import Any

from openai import OpenAI  # v1 SDK


def extract_resume_entities_with_llm(text: str) -> tuple[list[str], float | None, str | None, int | None, str]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
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
        client = OpenAI(api_key=api_key)
        # Use Chat Completions API (supported in v1). Avoid legacy module access.
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text},
            ],
        )
        raw = resp.choices[0].message.content if resp and resp.choices else "{}"
        
        # Ensure we have some content to parse
        if not raw or not raw.strip():
            error = "LLM returned empty response"
            raw = "{}"
        
        # Try to clean the response if it has markdown code blocks
        cleaned_raw = raw.strip()
        if cleaned_raw.startswith("```json"):
            cleaned_raw = cleaned_raw[7:]  # Remove ```json
        if cleaned_raw.endswith("```"):
            cleaned_raw = cleaned_raw[:-3]  # Remove ```
        cleaned_raw = cleaned_raw.strip()

        # Parse JSON if model complied, otherwise attempt best-effort extraction
        try:
            data: dict[str, Any] = json.loads(cleaned_raw or "{}")
        except json.JSONDecodeError as json_error:
            error = f"JSON parsing failed: {json_error}. Raw response: {raw[:200]}..."
            data = {}
            
        s = data.get("skills") or []
        if isinstance(s, list):
            skills = [str(x) for x in s if isinstance(x, (str, int, float))]
        y = data.get("years_experience")
        if isinstance(y, (int, float)):
            years = float(y)
    except Exception as e:
        error = str(e)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return skills, years, error, latency_ms, model


def generate_interview_questions_with_llm(track: str, context_text: str | None = None, count: int = 3, difficulty: str | None = None) -> tuple[list[str], str | None, int | None, str, list[dict[str, Any]] | None]:
    """
    Generate interview questions using an LLM given a track and optional context (e.g., resume_text).
    Returns (questions, error, latency_ms, model). On missing API key, returns empty questions and no error.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
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
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps(user_prompt)},
            ],
        )
        raw = resp.choices[0].message.content if resp and resp.choices else "{}"

        data: dict[str, Any] = json.loads(raw or "{}")
        q = data.get("questions") or []
        if isinstance(q, list):
            questions = [str(x).strip() for x in q if isinstance(x, (str, int, float))]
        its = data.get("items")
        if isinstance(its, list):
            structured_items = []
            for it in its:
                if isinstance(it, dict) and "text" in it:
                    structured_items.append({
                        "text": str(it.get("text", "")).strip(),
                        "topic": (None if it.get("topic") in (None, "") else str(it.get("topic"))),
                        "difficulty": (None if it.get("difficulty") in (None, "") else str(it.get("difficulty"))),
                    })
    except Exception as e:
        error = str(e)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return questions, error, latency_ms, model, structured_items


def analyze_domain_with_llm(
    *,
    user_profile: dict[str, Any],
    question_text: str | None,
    transcription: str,
) -> tuple[dict[str, Any], str | None, int | None, str]:
    """
    Perform domain knowledge analysis using LLM. Returns (analysis_json, error, latency_ms, model).
    Never raises; on missing API key returns empty analysis and no error.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
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

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps(user_content)},
            ],
        )
        raw = resp.choices[0].message.content if resp and resp.choices else "{}"
        data: dict[str, Any] = json.loads(raw or "{}")
        # Minimal sanity checks
        if isinstance(data.get("overall_score"), (int, float)):
            analysis = data
    except Exception as e:
        error = str(e)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return analysis, error, latency_ms, model


def analyze_communication_with_llm(
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
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
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

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )
        raw = resp.choices[0].message.content if resp and resp.choices else "{}"
        data: dict[str, Any] = json.loads(raw or "{}")
        if isinstance(data.get("overall_score"), (int, float)):
            analysis = data
    except Exception as e:
        error = str(e)

    latency_ms = int((time.perf_counter() - start) * 1000)
    return analysis, error, latency_ms, model

