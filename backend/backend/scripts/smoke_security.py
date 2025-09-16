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
    name = "Sec User"

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
        # Register and login user1
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users (u1)", r, err)
        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login (u1)", r, err)
        t1 = extract_token(safe_json(r) if r else {}) if (r and 200 <= r.status_code < 300) else None
        headers1 = auth_headers(t1)

        # Invalid auth
        r, err = safe_call(client, "GET", f"{API}/me")
        print_result("GET /api/me (no auth)", r, err)
        r, err = safe_call(client, "GET", f"{API}/me", headers={"Authorization": "Bearer invalid"})
        print_result("GET /api/me (invalid token)", r, err)

        # Duplicate user
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users (duplicate)", r, err)

        # Resume upload negatives
        files_bad = {"file": ("sample.bin", b"\x00\x01\x02", "application/octet-stream")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", files=files_bad)
        print_result("POST /api/extract-resume (unsupported type)", r, err)
        files_txt = {"file": ("sample.txt", b"hello", "text/plain")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", files=files_txt)
        print_result("POST /api/extract-resume (no auth)", r, err)

        # Create interview user1 and list with pagination
        r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers1, json={"track": "data_science"})
        print_result("POST /api/interviews/create (u1)", r, err)
        r, err = safe_call(client, "GET", f"{API}/interviews?limit=1", headers=headers1)
        print_result("GET /api/interviews (u1)", r, err)
        lb = safe_json(r) if r else {}
        first_id = lb.get("items", [{}])[0].get("interviewId") if isinstance(lb, dict) and lb.get("items") else None

        # Second user should not access first user's data
        email2 = f"{rand_str()}@example.com"
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email2, "password": password, "name": "User2"})
        print_result("POST /api/users (u2)", r, err)
        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email2, "password": password})
        print_result("POST /api/login (u2)", r, err)
        t2 = extract_token(safe_json(r) if r else {}) if (r and 200 <= r.status_code < 300) else None
        headers2 = auth_headers(t2)

        if first_id:
            r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions", headers=headers2)
            print_result("GET /api/interviews/{id}/questions (cross-user)", r, err)

        # Analysis auth failures
        r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers={"Authorization": "Bearer invalid_token"}, json={
            "question_attempt_id": 1,
            "analysis_types": ["domain"]
        })
        print_result("POST /api/complete-analysis (invalid token)", r, err)

        r, err = safe_call(client, "POST", f"{API}/complete-analysis", json={
            "question_attempt_id": 1, 
            "analysis_types": ["domain"]
        })
        print_result("POST /api/complete-analysis (no auth)", r, err)

        # Invalid inputs
        r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers1, json={
            "question_attempt_id": 1,
            "analysis_types": ["invalid_type", "also_invalid"]
        })
        print_result("POST /api/complete-analysis (invalid types)", r, err)

        r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers1, json={
            "question_attempt_id": 999999,
            "analysis_types": ["domain"]
        })
        print_result("POST /api/complete-analysis (non-existent QA)", r, err)

        # Invalid transcribe-whisper (non-existent QA)
        files_audio = {"file": ("Speech.mp3", b"\x00\x01", "audio/mpeg")}
        r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers1, files=files_audio, data={"question_attempt_id": 999999})
        print_result("POST /api/transcribe-whisper (non-existent QA)", r, err)


if __name__ == "__main__":
    main()


