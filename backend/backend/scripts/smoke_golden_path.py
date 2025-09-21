import os
import random
import string

import httpx

from scripts.smoke_utils import BASE_URL, API, safe_call, print_result, safe_json, extract_token, auth_headers


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def main() -> None:
    email = f"{rand_str()}@example.com"
    password = "pass123!"
    name = "E2E User"

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # Register
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        body = safe_json(r) if r else {}
        token = extract_token(body) if isinstance(body, dict) else None

        # Login
        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        body = safe_json(r) if r else {}
        login_token = extract_token(body) if isinstance(body, dict) else None
        token = login_token or token
        headers = auth_headers(token)

        # Me
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers)
        print_result("GET /api/me", r, err)

        # Update profile (form)
        form = {
            "degree": "B.Tech",
            "university": "Test Univ",
            "company": "Acme",
            "target_position": "Data Science",
            "years_experience": "1.5",
        }
        r, err = safe_call(client, "PUT", f"{API}/users/profile", headers=headers, data=form)
        print_result("PUT /api/users/profile", r, err)

        # Upload resume (text)
        files_txt = {"file": ("sample.txt", b"hello resume", "text/plain")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=files_txt)
        print_result("POST /api/extract-resume (text)", r, err)

        # Knowledge set
        r, err = safe_call(client, "GET", f"{API}/get_knowledgeset", headers=headers)
        print_result("GET /api/get_knowledgeset", r, err)

        # Read back my resume fields
        r, err = safe_call(client, "GET", f"{API}/me/resume", headers=headers)
        print_result("GET /api/me/resume", r, err)

        # Create interview (track + difficulty)
        r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "data_science", "difficulty": "medium"})
        print_result("POST /api/interviews/create", r, err)
        interview_id = None
        b = safe_json(r) if r else {}
        if isinstance(b, dict):
            interview_id = b.get("id") or b.get("interviewId") or b.get("interview_id")

        # Generate questions (use resume); include interview_id if available
        gen_payload = {"use_resume": True}
        if interview_id:
            gen_payload["interviewId"] = interview_id
        r, err = safe_call(client, "POST", f"{API}/interviews/generate-questions", headers=headers, json=gen_payload)
        print_result("POST /api/interviews/generate-questions", r, err)

        # Resume interview path
        r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "data_science"})
        print_result("POST /api/interviews/create (resume)", r, err)

        # List interviews (get current one id if missing)
        r, err = safe_call(client, "GET", f"{API}/interviews?limit=1", headers=headers)
        print_result("GET /api/interviews", r, err)
        lb = safe_json(r) if r else {}
        if not interview_id and isinstance(lb, dict) and lb.get("items"):
            interview_id = lb["items"][0].get("interviewId")

        # List questions for interview
        first_qid = None
        if interview_id:
            r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/questions?limit=3", headers=headers)
            print_result("GET /api/interviews/{id}/questions", r, err)
            qb = safe_json(r) if r else {}
            if isinstance(qb, dict) and qb.get("items"):
                item0 = qb["items"][0]
                if isinstance(item0, dict):
                    first_qid = item0.get("interviewQuestionId") or item0.get("interview_question_id")

        # Create attempt for first question
        qa_id = None
        if interview_id and first_qid:
            r, err = safe_call(client, "POST", f"{API}/interviews/{interview_id}/questions/{first_qid}/attempts", headers=headers, json={"start_time": None})
            print_result("POST /api/interviews/{id}/questions/{qid}/attempts", r, err)
            ab = safe_json(r) if r else {}
            if isinstance(ab, dict):
                qa_id = ab.get("questionAttemptId") or ab.get("question_attempt_id")

        # List question attempts
        if interview_id:
            r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/question-attempts", headers=headers)
            print_result("GET /api/interviews/{id}/question-attempts", r, err)

        # Transcribe audio for that attempt if assets/Speech.mp3 exists
        if qa_id:
            speech_file_path = os.path.join("assets", "Speech.mp3")
            if os.path.exists(speech_file_path):
                with open(speech_file_path, "rb") as audio_file:
                    files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                    data = {"question_attempt_id": qa_id, "language": "en"}
                    r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=data)
                    print_result("POST /api/transcribe-whisper", r, err)

        # Complete analysis (domain + communication + pace + pause)
        if qa_id:
            payload = {"question_attempt_id": qa_id, "analysis_types": ["domain", "communication", "pace", "pause"]}
            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=payload)
            print_result("POST /api/complete-analysis", r, err)

            # Individual analysis endpoints
            r, err = safe_call(client, "POST", f"{API}/domain-base-analysis", headers=headers, json={"question_attempt_id": qa_id})
            print_result("POST /api/domain-base-analysis", r, err)
            r, err = safe_call(client, "POST", f"{API}/communication-based-analysis", headers=headers, json={"question_attempt_id": qa_id})
            print_result("POST /api/communication-based-analysis", r, err)
            r, err = safe_call(client, "POST", f"{API}/analyze-pace", headers=headers, json={"question_attempt_id": qa_id})
            print_result("POST /api/analyze-pace", r, err)
            r, err = safe_call(client, "POST", f"{API}/analyze-pause", headers=headers, json={"question_attempt_id": qa_id})
            print_result("POST /api/analyze-pause", r, err)

        # Final report
        if interview_id:
            r, err = safe_call(client, "POST", f"{API}/final-report", headers=headers, json={"interviewId": interview_id})
            print_result("POST /api/final-report", r, err)
            r2, err2 = safe_call(client, "GET", f"{API}/final-report/{interview_id}", headers=headers)
            print_result("GET /api/final-report/{id}", r2, err2)


if __name__ == "__main__":
    main()


