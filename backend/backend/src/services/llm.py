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


