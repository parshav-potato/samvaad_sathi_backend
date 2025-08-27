import json
import os
import time
from typing import Any


def extract_resume_entities_with_llm(text: str) -> tuple[list[str], float | None, str | None, int | None, str]:
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not text:
        return [], None, None, None, model

    start = time.perf_counter()
    error: str | None = None
    skills: list[str] = []
    years: float | None = None

    prompt = (
        "Extract skills (array of strings) and total years of professional experience "
        "as a number from the resume text. Return ONLY valid JSON with keys: "
        "skills (string[]), years_experience (number|null)."
    )
    input_text = text[:20000]

    try:
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": input_text},
                ],
            )
            raw = resp.choices[0].message.content if resp and resp.choices else "{}"
        except Exception:
            import openai  # type: ignore

            openai.api_key = api_key
            comp = openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                temperature=0,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": input_text},
                ],
            )
            raw = comp["choices"][0]["message"]["content"]

        data: dict[str, Any] = json.loads(raw or "{}")
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


def generate_interview_questions_with_llm(track: str, context_text: str | None = None, count: int = 3) -> tuple[list[str], str | None, int | None, str, list[dict[str, Any]] | None]:
    """
    Generate interview questions using an LLM given a track and optional context (e.g., resume_text).
    Returns (questions, error, latency_ms, model). On missing API key, returns empty questions and no error.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return [], None, None, model

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
        "constraints": [
            "No preambles, no numbering in the JSON itself",
            "Questions should be single sentences when possible",
            "Avoid duplicate or trivial questions",
        ],
    }

    try:
        try:
            from openai import OpenAI  # type: ignore

            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            )
            raw = resp.choices[0].message.content if resp and resp.choices else "{}"
        except Exception:
            import openai  # type: ignore

            openai.api_key = api_key
            comp = openai.ChatCompletion.create(
                model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                temperature=0.2,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps(user_prompt)},
                ],
            )
            raw = comp["choices"][0]["message"]["content"]

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

