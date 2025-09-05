import io
import re
import os
import time
import hashlib
from typing import Any, Dict, Tuple

import fastapi
import PyPDF2
from src.api.dependencies.repository import get_repository
from src.repository.crud.user import UserCRUDRepository
from src.services.llm import extract_resume_entities_with_llm

from src.api.dependencies.auth import get_current_user
from src.models.schemas.resume import ResumeExtractionResponse, MyResumeResponse, KnowledgeSetResponse


router = fastapi.APIRouter(prefix="", tags=["resume"])


@router.post(
    path="/extract-resume",
    name="resume:extract-resume",
    response_model=ResumeExtractionResponse,
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    summary="Upload a resume and extract skills/experience",
    description=(
        "Accepts a PDF or plain text file (<=5MB). Extracts text, calls an LLM to detect raw skills and years of "
        "experience, validates and normalizes results, and persists them to the authenticated user's profile."
    ),
)
async def extract_resume(
    file: fastapi.UploadFile = fastapi.File(
        ..., description="Resume file to upload. Allowed types: application/pdf, text/plain (max 5MB)"
    ),
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
            # Primary extraction with PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(raw_bytes))
            texts: list[str] = []
            
            # Check if PDF has pages
            if len(pdf_reader.pages) == 0:
                extracted_text = ""
            else:
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text() or ""
                        if page_text.strip():  # Only add non-empty pages
                            texts.append(page_text)
                    except Exception as page_error:
                        # Log page extraction error but continue with other pages
                        print(f"Warning: Failed to extract text from page {page_num + 1}: {page_error}")
                        continue
                
                extracted_text = "\n".join(texts)
                
                # If no text extracted, try pdfplumber as fallback
                if not extracted_text.strip():
                    try:
                        import pdfplumber
                        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                            fallback_texts = []
                            for page in pdf.pages:
                                page_text = page.extract_text()
                                if page_text and page_text.strip():
                                    fallback_texts.append(page_text)
                            extracted_text = "\n".join(fallback_texts)
                    except ImportError:
                        print("Warning: pdfplumber not available for fallback PDF extraction")
                    except Exception as fallback_error:
                        print(f"Warning: pdfplumber fallback failed: {fallback_error}")
                        
        except Exception as pdf_error:
            print(f"PDF extraction error: {pdf_error}")
            # Final fallback: try pdfplumber directly
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                    fallback_texts = []
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            fallback_texts.append(page_text)
                    extracted_text = "\n".join(fallback_texts)
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



@router.get(
    path="/me/resume",
    name="resume:get-my-resume",
    response_model=MyResumeResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Get my saved resume data",
    description="Returns only the authenticated user's saved resume fields and basic metadata.",
)
async def get_my_resume(
    current_user=fastapi.Depends(get_current_user),
):
    skills_field = current_user.skills if isinstance(current_user.skills, dict) else None
    items = skills_field.get("items", []) if skills_field else []
    if not isinstance(items, list):
        items = []

    return {
        "id": current_user.id,
        "email": current_user.email,
        "years_experience": current_user.years_experience,
        "skills": items,
        "has_resume_text": bool(current_user.resume_text),
        "text_length": len(current_user.resume_text or ""),
    }


@router.get(
    path="/get_knowledgeset",
    name="resume:get-knowledge-set",
    response_model=KnowledgeSetResponse,
    status_code=fastapi.status.HTTP_200_OK,
    summary="Derive a knowledge set from my resume",
    description=(
        "Uses the authenticated user's saved resume_text to produce a normalized skills list (knowledge set). "
        "Results are cached in-memory per user and resume content hash."
    ),
)
async def get_knowledge_set(
    current_user=fastapi.Depends(get_current_user),
):
    """
    Returns a knowledge set (normalized list of skills) derived from the authenticated user's resume.
    Access control: self-only (uses current_user from auth). Stateless operation for ECS compatibility.
    """
    # Use stored resume text if available
    resume_text = current_user.resume_text or ""
    normalized_text = re.sub(r"\s+", " ", resume_text).strip()

    if not normalized_text:
        return {
            "ok": False,
            "error": "No resume_text available for current user",
            "knowledge_set": {"items": []},
            "cached": False,
        }

    # Generate knowledge set directly (stateless - no caching for ECS compatibility)
    cached = False
    
    # Reuse LLM extraction service to get skills; ignore years here
    from src.services.llm import extract_resume_entities_with_llm  # local import to avoid cycles

    skills, _years, llm_error, llm_latency_ms, llm_model = extract_resume_entities_with_llm(normalized_text)

    # Normalize and validate
    def _norm_skill(s: str) -> str:
        return re.sub(r"\s+", " ", str(s)).strip().lower()

    normalized_skills: list[str] = []
    seen: set[str] = set()
    warnings: list[str] = []
    for s in skills or []:
        s_norm = _norm_skill(s)
        if not s_norm:
            continue
        if not re.search(r"[a-z]", s_norm):
            warnings.append(f"dropped skill without letters: '{s}'")
            continue
        if len(s_norm) < 2 or len(s_norm) > 64:
            warnings.append(f"dropped skill length out of range: '{s}'")
            continue
        if s_norm not in seen:
            seen.add(s_norm)
            normalized_skills.append(s_norm)

    result = {
        "knowledge_set": {"items": normalized_skills},
        "llm_model": llm_model,
        "llm_latency_ms": llm_latency_ms,
        "llm_error": llm_error,
        "warnings": warnings,
    }

    return {"ok": True, "cached": cached, **result}

