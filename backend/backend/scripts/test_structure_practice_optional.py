#!/usr/bin/env python3
"""
Quick test to verify structure-practice endpoint works with optional interview_id
"""
import httpx
import json
import sys
import random
import string


API = "http://localhost:8000/api"


def safe_call(client, method, url, **kwargs):
    """Helper to safely call API and return response or error"""
    try:
        if method == "GET":
            r = client.get(url, **kwargs)
        elif method == "POST":
            r = client.post(url, **kwargs)
        elif method == "PUT":
            r = client.put(url, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")
        return r, None
    except Exception as e:
        return None, str(e)


def print_result(name, r, err):
    """Pretty print result"""
    if err:
        print(json.dumps({"name": name, "error": err, "ok": False}))
        return
    try:
        body = r.json()
    except:
        body = r.text
    print(json.dumps({"name": name, "status": r.status_code, "ok": r.is_success, "body": body}))


def main():
    with httpx.Client(timeout=120.0) as client:
        # Step 1: Register test user
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"structure_test_{random_suffix}@example.com"
        r, err = safe_call(
            client,
            "POST",
            f"{API}/users",
            json={"email": email, "password": "test123", "name": "Structure Test User"},
        )
        print_result("POST /api/users", r, err)
        if err or not r.is_success:
            raise SystemExit("Failed to register user")
        
        # Step 2: Login
        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": "test123"})
        print_result("POST /api/login", r, err)
        if err or not r.is_success:
            raise SystemExit("Failed to login")
        token = r.json()["authorizedUser"]["token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 3: Test structure-practice WITHOUT interview_id (should return cached response)
        r, err = safe_call(
            client,
            "POST",
            f"{API}/v2/interviews/structure-practice",
            headers=headers,
            json={},  # No interview_id
        )
        print_result("POST /api/v2/interviews/structure-practice (no interview_id)", r, err)
        
        if err or not r.is_success:
            raise SystemExit("Failed to get cached structure practice")
        
        response_data = r.json()
        
        # Validate cached response
        if not response_data.get("cached"):
            raise SystemExit("Expected cached=true in response")
        
        if response_data.get("interviewId") is not None:
            raise SystemExit("Expected interviewId to be null in cached response")
        
        if response_data.get("count") != 5:
            raise SystemExit(f"Expected 5 cached questions, got {response_data.get('count')}")
        
        print(f"✅ Cached response validated: {response_data['count']} questions, cached={response_data['cached']}")
        
        # Step 4: Create an actual interview to test WITH interview_id
        r, err = safe_call(
            client,
            "POST",
            f"{API}/v2/interviews/create",
            headers=headers,
            json={"track": "javascript developer", "difficulty": "medium"},
        )
        print_result("POST /api/v2/interviews/create", r, err)
        if err or not r.is_success:
            raise SystemExit("Failed to create interview")
        
        interview_id = r.json()["interviewId"]
        
        # Step 5: Generate questions
        r, err = safe_call(
            client,
            "POST",
            f"{API}/v2/interviews/generate-questions",
            headers=headers,
            json={"interviewId": interview_id, "count": 3},
        )
        print_result("POST /api/v2/interviews/generate-questions", r, err)
        if err or not r.is_success:
            raise SystemExit("Failed to generate questions")
        
        # Step 6: Test structure-practice WITH interview_id
        r, err = safe_call(
            client,
            "POST",
            f"{API}/v2/interviews/structure-practice",
            headers=headers,
            json={"interview_id": interview_id},
        )
        print_result("POST /api/v2/interviews/structure-practice (with interview_id)", r, err)
        
        if err or not r.is_success:
            raise SystemExit("Failed to get structure practice with interview_id")
        
        response_data = r.json()
        
        # Validate non-cached response
        if response_data.get("cached"):
            raise SystemExit("Expected cached=false when interview_id provided")
        
        if response_data.get("interviewId") != interview_id:
            raise SystemExit(f"Expected interviewId={interview_id}, got {response_data.get('interviewId')}")
        
        if response_data.get("count") < 1:
            raise SystemExit(f"Expected at least 1 question, got {response_data.get('count')}")
        
        print(f"✅ Interview-based response validated: {response_data['count']} questions, cached={response_data['cached']}")
        print("\n✅ All tests passed! Structure-practice endpoint works with optional interview_id")


if __name__ == "__main__":
    main()
