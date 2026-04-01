from __future__ import annotations

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


def rand_email(prefix: str = "analytics") -> str:
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}_{token}@example.com"


def _get_user_id(me_body: dict) -> int | None:
    if not isinstance(me_body, dict):
        return None
    for key in ("userId", "user_id", "id"):
        value = me_body.get(key)
        if isinstance(value, int):
            return value
    return None


def _get_interview_id(body: dict) -> int | None:
    if not isinstance(body, dict):
        return None
    for key in ("id", "interviewId", "interview_id"):
        value = body.get(key)
        if isinstance(value, int):
            return value
    return None


def main() -> None:
    password = "pass123!"
    email = rand_email()

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # Register + login
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": "Analytics Smoke User"})
        print_result("POST /api/users", r, err)

        reg_token = extract_token(safe_json(r) if r else {})

        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        login_token = extract_token(safe_json(r) if r else {})
        token = login_token or reg_token

        if not token:
            raise SystemExit("Could not obtain token for analytics smoke tests")

        headers = auth_headers(token)

        # Profile (helps role-segment coverage)
        profile_payload = {
            "degree": "B.Tech",
            "university": "Analytics Test College",
            "target_position": "Backend Development",
            "years_experience": 1.0,
        }
        r, err = safe_call(client, "PUT", f"{API}/users/profile", headers=headers, json=profile_payload)
        print_result("PUT /api/users/profile", r, err)

        # me -> user_id for student analytics
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers)
        print_result("GET /api/me", r, err)
        me_body = safe_json(r) if r else {}
        user_id = _get_user_id(me_body)
        if not user_id:
            raise SystemExit("Could not resolve user id from /api/me response")

        # Create + complete interview to produce some lifecycle events
        r, err = safe_call(
            client,
            "POST",
            f"{API}/interviews/create",
            headers=headers,
            json={"track": "backend_development", "difficulty": "easy"},
        )
        print_result("POST /api/interviews/create", r, err)
        create_body = safe_json(r) if r else {}
        interview_id = _get_interview_id(create_body)

        if interview_id:
            r, err = safe_call(client, "POST", f"{API}/interviews/complete", headers=headers, json={"interviewId": interview_id})
            print_result("POST /api/interviews/complete", r, err)

        # Analytics endpoints
        r, err = safe_call(client, "GET", f"{API}/analytics/student/{user_id}", headers=headers)
        print_result("GET /api/analytics/student/{user_id}", r, err)
        if not r or r.status_code != 200:
            raise SystemExit("Student analytics endpoint failed")

        if interview_id:
            r, err = safe_call(client, "GET", f"{API}/analytics/interview/{interview_id}", headers=headers)
            print_result("GET /api/analytics/interview/{interview_id}", r, err)

        r, err = safe_call(client, "GET", f"{API}/analytics/segment/role", headers=headers)
        print_result("GET /api/analytics/segment/role", r, err)

        r, err = safe_call(client, "GET", f"{API}/analytics/segment/difficulty", headers=headers)
        print_result("GET /api/analytics/segment/difficulty", r, err)

        r, err = safe_call(client, "GET", f"{API}/analytics/segment/college", headers=headers)
        print_result("GET /api/analytics/segment/college", r, err)

        r, err = safe_call(client, "GET", f"{API}/analytics/system", headers=headers)
        print_result("GET /api/analytics/system", r, err)

        r, err = safe_call(client, "GET", f"{API}/analytics/scoring", headers=headers)
        print_result("GET /api/analytics/scoring", r, err)

        r, err = safe_call(client, "GET", f"{API}/analytics/alerts", headers=headers)
        print_result("GET /api/analytics/alerts", r, err)

        # Report engagement event endpoint
        engagement_payload = {
            "interviewId": interview_id,
            "timeSpentSeconds": 42,
            "recommendationClicks": 3,
            "reportType": "summary_v2",
        }
        r, err = safe_call(client, "POST", f"{API}/analytics/report-engagement", headers=headers, json=engagement_payload)
        print_result("POST /api/analytics/report-engagement", r, err)
        if not r or r.status_code != 200:
            raise SystemExit("Report engagement tracking endpoint failed")

        # Negative auth check
        r, err = safe_call(client, "GET", f"{API}/analytics/system")
        print_result("GET /api/analytics/system (no auth)", r, err)


if __name__ == "__main__":
    main()
