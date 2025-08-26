import io
import re
import os
import time

import fastapi
import PyPDF2
from src.api.dependencies.repository import get_repository
from src.repository.crud.user import UserCRUDRepository
from src.services.llm import extract_resume_entities_with_llm

from src.api.dependencies.auth import get_current_user


router = fastapi.APIRouter(prefix="", tags=["resume"])


@router.post(
    path="/extract-resume",
    name="resume:extract-resume",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
)
async def extract_resume(
    file: fastapi.UploadFile = fastapi.File(...),
    current_user=fastapi.Depends(get_current_user),
    user_repo: UserCRUDRepository = fastapi.Depends(get_repository(repo_type=UserCRUDRepository)),
):
    allowed_types = {"application/pdf", "text/plain"}
    content_type = file.content_type or ""

    if content_type not in allowed_types:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {content_type}",
        )

    # Enforce a max upload size of 5 MB while buffering content
    max_bytes = 5 * 1024 * 1024
    total_size = 0
    buffer = bytearray()
    chunk_size = 1024 * 64
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > max_bytes:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploaded file exceeds 5 MB limit",
            )
        buffer.extend(chunk)

    raw_bytes = bytes(buffer)

    # Extract text depending on the content type
    extracted_text = ""
    if content_type == "text/plain":
        extracted_text = raw_bytes.decode("utf-8", errors="ignore")
    elif content_type == "application/pdf":
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            texts: list[str] = []
            for page in pdf_reader.pages:
                page_text = page.extract_text() or ""
                texts.append(page_text)
            extracted_text = "\n".join(texts)
        except Exception:
            extracted_text = ""

    # Normalize whitespace and control characters
    normalized = re.sub(r"\s+", " ", extracted_text or "").strip()
    preview = normalized[:300]

    # LLM extraction via service
    skills, years_experience, llm_error, llm_latency_ms, llm_model = extract_resume_entities_with_llm(normalized)

    # Validation & structuring
    warnings: list[str] = []

    def _norm_skill(s: str) -> str:
        s2 = re.sub(r"\s+", " ", s).strip().lower()
        return s2

    normalized_skills: list[str] = []
    seen: set[str] = set()
    for s in skills:
        s_str = _norm_skill(str(s))
        if not s_str:
            continue
        if not re.search(r"[a-z]", s_str):
            warnings.append(f"dropped skill without letters: '{s}'")
            continue
        if len(s_str) < 2 or len(s_str) > 64:
            warnings.append(f"dropped skill length out of range: '{s}'")
            continue
        if s_str not in seen:
            seen.add(s_str)
            normalized_skills.append(s_str)

    validated_years: float | None = None
    if years_experience is not None:
        try:
            validated_years = float(years_experience)
            if validated_years < 0:
                warnings.append("years_experience below 0; clamped to 0.0")
                validated_years = 0.0
            if validated_years > 50:
                warnings.append("years_experience above 50; clamped to 50.0")
                validated_years = 50.0
            validated_years = round(validated_years, 1)
        except Exception:
            validated_years = None
    else:
        # Try a simple fallback from text if LLM omitted
        m3 = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*years?", normalized, flags=re.I)
        if m3:
            try:
                v = float(m3.group(1))
                validated_years = max(0.0, min(50.0, round(v, 1)))
                warnings.append("years_experience inferred via regex fallback")
            except Exception:
                validated_years = None

    response = {
        "filename": file.filename,
        "content_type": content_type,
        "size": total_size,
        "text_length": len(normalized),
        "preview": preview,
        "skills": skills,
        "years_experience": years_experience,
        "llm_model": llm_model,
        "llm_latency_ms": llm_latency_ms,
        "llm_error": llm_error,
        "validated": {
            "skills": normalized_skills,
            "years_experience": validated_years,
            "warnings": warnings,
        },
        "message": "File received and text extracted.",
    }

    # Persist validated data to User model
    try:
        await user_repo.update_resume_data(
            user_id=current_user.id,
            resume_text=normalized if normalized else None,
            years_experience=validated_years,
            skills=normalized_skills,
        )
        response["saved"] = True
    except Exception as e:
        response["saved"] = False
        response["save_error"] = str(e)

    return response


