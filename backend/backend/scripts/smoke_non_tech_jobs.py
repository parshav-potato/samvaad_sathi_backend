"""Smoke test for global job profiles + non-tech interview generation flow."""

from __future__ import annotations

import json
import random
import string

import httpx

from scripts.smoke_utils import (
    API,
    BASE_URL,
    auth_headers,
    extract_token,
    print_result,
    safe_call,
    safe_json,
)


def rand_email() -> str:
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"nontech_{token}@example.com"


def main() -> None:
    email = rand_email()
    password = "pass123!"
    name = "Non Tech Smoke User"

    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        token = extract_token(safe_json(r) if r else {}) if not err else None

        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        login_body = safe_json(r) if r else {}
        token = extract_token(login_body) or token
        headers = auth_headers(token)

        resume_files = {"file": ("sample.txt", b"non tech smoke resume: stakeholder communication leadership", "text/plain")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=resume_files)
        print_result("POST /api/extract-resume", r, err)

        create_payload = {
            "jobName": "Product Manager",
            "jobDescription": "Lead cross-functional initiatives, prioritize roadmap, coordinate stakeholders, and drive outcomes.",
            "companyName": "Acme Corp",
            "experienceLevel": "mid",
            "skills": ["communication", "prioritization", "stakeholder-management"],
            "additionalContext": "Focus on non-technical behavioral and situational interview prompts.",
        }
        r, err = safe_call(client, "POST", f"{API}/v2/job-profiles", headers=headers, json=create_payload)
        print_result("POST /api/v2/job-profiles", r, err)
        created = safe_json(r) if r else {}
        job_profile_id = created.get("jobProfileId") or created.get("job_profile_id")
        if not job_profile_id:
            raise SystemExit("Failed to create job profile")

        r, err = safe_call(client, "GET", f"{API}/v2/job-profiles", headers=headers)
        print_result("GET /api/v2/job-profiles", r, err)
        listed = safe_json(r) if r else {}
        items = listed.get("items", []) if isinstance(listed, dict) else []
        if not any((item.get("jobProfileId") or item.get("job_profile_id")) == job_profile_id for item in items):
            raise SystemExit("Created job profile not found in list endpoint")

        gen_payload = {
            "jobProfileId": job_profile_id,
            "difficulty": "medium",
            "useResume": True,
        }
        r, err = safe_call(client, "POST", f"{API}/v2/interviews/non-tech/generate-questions", headers=headers, json=gen_payload)
        print_result("POST /api/v2/interviews/non-tech/generate-questions", r, err)
        gen = safe_json(r) if r else {}
        q_items = gen.get("items", []) if isinstance(gen, dict) else []
        if len(q_items) != 5:
            raise SystemExit(f"Expected 5 generated questions, got {len(q_items)}")

        follow_up_ready = [q for q in q_items if q.get("followUpStrategy") or q.get("follow_up_strategy")]
        if len(follow_up_ready) < 2:
            raise SystemExit("Expected at least 2 follow-up enabled questions in non-tech flow")

        print(json.dumps({
            "name": "non-tech-generation-check",
            "question_count": len(q_items),
            "follow_up_ready": len(follow_up_ready),
            "interview_id": gen.get("interviewId") or gen.get("interview_id"),
            "track": gen.get("track"),
        }))

        r, err = safe_call(client, "DELETE", f"{API}/v2/job-profiles/{job_profile_id}", headers=headers)
        print_result("DELETE /api/v2/job-profiles/{id}", r, err)
        deleted = safe_json(r) if r else {}
        if not deleted.get("deleted"):
            raise SystemExit("Delete endpoint did not report deletion")


if __name__ == "__main__":
    main()
