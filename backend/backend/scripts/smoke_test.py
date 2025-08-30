import json
import random
import string
from datetime import datetime

import httpx

BASE_URL = "http://127.0.0.1:8000"
API = "/api"


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def print_result(name: str, resp: httpx.Response | None, error: str | None = None) -> None:
    if error is not None:
        print(json.dumps({"name": name, "status": None, "ok": False, "error": error}))
        return
    ok = 200 <= resp.status_code < 300 if resp is not None else False
    print(json.dumps({
        "name": name,
        "status": None if resp is None else resp.status_code,
        "ok": ok,
        "body": None if resp is None else safe_json(resp)
    }, default=str))


def safe_json(resp: httpx.Response):
    try:
        return resp.json()
    except Exception:
        return (resp.text or "")[:300]


def safe_call(client: httpx.Client, method: str, url: str, **kwargs) -> tuple[httpx.Response | None, str | None]:
    try:
        r = client.request(method, url, **kwargs)
        return r, None
    except Exception as e:
        return None, str(e)


def extract_token(body: dict) -> str | None:
    for key in ("authorizedUser", "authorized_user", "authorizedAccount", "authorized_account"):
        if key in body and isinstance(body[key], dict) and "token" in body[key]:
            return body[key]["token"]
    return None


def main() -> None:
    email = f"{rand_str()}@example.com"
    password = "pass123!"
    name = "Smoke User"

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        r, err = safe_call(client, "GET", "/docs")
        print_result("GET /docs", r, err)

        # Users register/login/me
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        user_id = r.json().get("id") if (r and 200 <= r.status_code < 300) else None
        user_token = extract_token(r.json()) if (r and 200 <= r.status_code < 300) else None

        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        login_token = extract_token(r.json()) if (r and 200 <= r.status_code < 300) else None

        token = login_token or user_token
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        headers_invalid = {"Authorization": "Bearer invalid"}
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers)
        print_result("GET /api/me", r, err)

        # Negative: missing/invalid auth
        r, err = safe_call(client, "GET", f"{API}/me")
        print_result("GET /api/me (no auth)", r, err)
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers_invalid)
        print_result("GET /api/me (invalid token)", r, err)

        # Resume upload (requires auth)
        if token:
            files_txt = {"file": ("sample.txt", b"hello resume", "text/plain")}
            r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=files_txt)
            print_result("POST /api/extract-resume (text)", r, err)

            # New: self-only read of resume fields
            r, err = safe_call(client, "GET", f"{API}/me/resume", headers=headers)
            print_result("GET /api/me/resume", r, err)

            # New: knowledge set extraction (cached on repeat calls)
            r, err = safe_call(client, "GET", f"{API}/get_knowledgeset", headers=headers)
            print_result("GET /api/get_knowledgeset", r, err)

            # Repeat call to check caching flag path
            r, err = safe_call(client, "GET", f"{API}/get_knowledgeset", headers=headers)
            print_result("GET /api/get_knowledgeset (cached)", r, err)

            files_pdf = {"file": ("sample.pdf", b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n", "application/pdf")}
            r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=files_pdf)
            print_result("POST /api/extract-resume (pdf)", r, err)

            files_bad = {"file": ("sample.bin", b"\x00\x01\x02", "application/octet-stream")}
            r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=files_bad)
            print_result("POST /api/extract-resume (unsupported type)", r, err)

            r, err = safe_call(client, "POST", f"{API}/extract-resume", files=files_txt)
            print_result("POST /api/extract-resume (no auth)", r, err)

            # Interviews: create/resume with difficulty
            r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "data_science", "difficulty": "hard"})
            print_result("POST /api/interviews/create", r, err)
            # Repeat to verify resume path
            r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "data_science"})
            print_result("POST /api/interviews/create (resume)", r, err)

            # Interviews: generate questions
            r, err = safe_call(client, "POST", f"{API}/interviews/generate-questions", headers=headers)
            print_result("POST /api/interviews/generate-questions", r, err)

            # Test generate questions without resume
            r, err = safe_call(client, "POST", f"{API}/interviews/generate-questions", headers=headers, json={"use_resume": False})
            print_result("POST /api/interviews/generate-questions (no resume)", r, err)

            # Create another interview (different track) for pagination
            r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "ml_engineering", "difficulty": "easy"})
            print_result("POST /api/interviews/create (second track)", r, err)

            # Interviews: list sessions (cursor pagination)
            r, err = safe_call(client, "GET", f"{API}/interviews?limit=1", headers=headers)
            print_result("GET /api/interviews", r, err)
            body = safe_json(r) if r else {}
            if isinstance(body, dict) and body.get("items"):
                first_id = body["items"][0]["id"]
                next_cursor = body.get("next_cursor")
                # Interviews: list questions for the first interview
                r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions?limit=2", headers=headers)
                print_result("GET /api/interviews/{id}/questions", r, err)
                qb = safe_json(r) if r else {}
                if isinstance(qb, dict) and qb.get("next_cursor") is not None:
                    # follow next_cursor once
                    nc = qb.get("next_cursor")
                    r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions?limit=2&cursor={nc}", headers=headers)
                    print_result("GET /api/interviews/{id}/questions (page 2)", r, err)
                    qb2 = safe_json(r) if r else {}
                    if isinstance(qb2, dict) and qb2.get("next_cursor") is not None:
                        nc2 = qb2.get("next_cursor")
                        r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions?limit=2&cursor={nc2}", headers=headers)
                        print_result("GET /api/interviews/{id}/questions (page 3)", r, err)

                # If we have a next_cursor for interviews, follow it once
                if next_cursor is not None:
                    r, err = safe_call(client, "GET", f"{API}/interviews?limit=1&cursor={next_cursor}", headers=headers)
                    print_result("GET /api/interviews (page 2)", r, err)

            # Interviews: complete session
            r, err = safe_call(client, "POST", f"{API}/interviews/complete", headers=headers)
            print_result("POST /api/interviews/complete", r, err)

            # Cross-user access negative: second user should not access first user's interview/questions
            email2 = f"{rand_str()}@example.com"
            r, err = safe_call(client, "POST", f"{API}/users", json={"email": email2, "password": password, "name": "User2"})
            print_result("POST /api/users (u2)", r, err)
            r, err = safe_call(client, "POST", f"{API}/login", json={"email": email2, "password": password})
            print_result("POST /api/login (u2)", r, err)
            t2 = extract_token(safe_json(r) if r else {}) if (r and 200 <= r.status_code < 300) else None
            headers2 = {"Authorization": f"Bearer {t2}"} if t2 else {}
            if isinstance(body, dict) and body.get("items"):
                # first_id from earlier
                r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions", headers=headers2)
                print_result("GET /api/interviews/{id}/questions (cross-user)", r, err)

        # Negative: wrong password login
        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": "wrong"})
        print_result("POST /api/login (wrong password)", r, err)

        # Duplicate users register
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users (duplicate)", r, err)

        # Clean up (end of tests)
        print("\n" + "="*50 + " SMOKE TEST COMPLETE " + "="*50)


if __name__ == "__main__":
    main()
