"""Smoke tests for pronunciation practice feature."""

from __future__ import annotations

import json
import random
import string
from pathlib import Path

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
    return f"pronunciation_{token}@example.com"


def main() -> None:
    """Test complete pronunciation practice flow: create session and get audio."""
    email = rand_email()
    password = "pass123!"
    name = "Pronunciation Test User"

    with httpx.Client(base_url=BASE_URL, timeout=90.0) as client:
        # Register & login
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        token = extract_token(safe_json(r) if r else {}) if not err else None

        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        login_body = safe_json(r) if r else {}
        token = extract_token(login_body) or token
        headers = auth_headers(token)

        # Test 1: Create pronunciation practice session (easy)
        create_payload = {"difficulty": "easy"}
        r, err = safe_call(
            client, "POST", f"{API}/v2/pronunciation/create", headers=headers, json=create_payload
        )
        print_result("POST /api/v2/pronunciation/create (easy)", r, err)
        
        if not r or r.status_code != 201:
            raise SystemExit(f"Failed to create pronunciation practice session: {r.status_code if r else 'no response'}")
        
        practice_data = safe_json(r)
        practice_id = practice_data.get("practiceId")  # camelCase from API
        words = practice_data.get("words", [])
        difficulty = practice_data.get("difficulty")
        status = practice_data.get("status")
        
        # Validate response structure
        if not practice_id or not words:
            raise SystemExit(f"Invalid response structure: {practice_data}")
        
        if difficulty != "easy":
            raise SystemExit(f"Expected difficulty 'easy', got '{difficulty}'")
        
        if status != "active":
            raise SystemExit(f"Expected status 'active', got '{status}'")
        
        if len(words) != 10:
            raise SystemExit(f"Expected 10 words, got {len(words)}")
        
        # Validate word structure
        for idx, word_obj in enumerate(words):
            if word_obj.get("index") != idx:
                raise SystemExit(f"Word index mismatch at position {idx}")
            if not word_obj.get("word"):
                raise SystemExit(f"Missing word at index {idx}")
            if not word_obj.get("phonetic"):
                raise SystemExit(f"Missing phonetic at index {idx}")
        
        print(f"✓ Created practice session {practice_id} with {len(words)} words")
        print(f"  First word: {words[0]['word']} ({words[0]['phonetic']})")
        
        # Test 2: Get audio for first word (normal speed)
        r, err = safe_call(
            client, "GET", f"{API}/v2/pronunciation/{practice_id}/audio/0", headers=headers
        )
        print_result("GET /api/v2/pronunciation/{id}/audio/0 (normal)", r, err)
        
        if not r or r.status_code != 200:
            raise SystemExit(f"Failed to get audio: {r.status_code if r else 'no response'}")
        
        # Check content type
        content_type = r.headers.get("content-type")
        if content_type != "audio/ogg":
            raise SystemExit(f"Expected audio/ogg, got {content_type}")
        
        # Check audio size
        audio_size = len(r.content)
        if audio_size == 0:
            raise SystemExit("Empty audio response")
        
        latency_ms = r.headers.get("x-audio-latency-ms", "N/A")
        print(f"✓ Received audio ({audio_size} bytes, latency: {latency_ms}ms)")
        
        # Test 3: Get audio for first word (slow speed)
        r, err = safe_call(
            client, "GET", f"{API}/v2/pronunciation/{practice_id}/audio/0?slow=true", headers=headers
        )
        print_result("GET /api/v2/pronunciation/{id}/audio/0 (slow)", r, err)
        
        if not r or r.status_code != 200:
            raise SystemExit(f"Failed to get slow audio: {r.status_code if r else 'no response'}")
        
        slow_audio_size = len(r.content)
        if slow_audio_size == 0:
            raise SystemExit("Empty slow audio response")
        
        latency_ms = r.headers.get("x-audio-latency-ms", "N/A")
        print(f"✓ Received slow audio ({slow_audio_size} bytes, latency: {latency_ms}ms)")
        
        # Test 4: Test medium difficulty
        r, err = safe_call(
            client, "POST", f"{API}/v2/pronunciation/create", headers=headers, json={"difficulty": "medium"}
        )
        print_result("POST /api/v2/pronunciation/create (medium)", r, err)
        
        if not r or r.status_code != 201:
            raise SystemExit("Failed to create medium practice")
        
        medium_data = safe_json(r)
        if medium_data.get("difficulty") != "medium":
            raise SystemExit("Expected medium difficulty")
        
        print(f"✓ Created medium practice session {medium_data['practiceId']}")
        
        # Test 5: Test hard difficulty
        r, err = safe_call(
            client, "POST", f"{API}/v2/pronunciation/create", headers=headers, json={"difficulty": "hard"}
        )
        print_result("POST /api/v2/pronunciation/create (hard)", r, err)
        
        if not r or r.status_code != 201:
            raise SystemExit("Failed to create hard practice")
        
        hard_data = safe_json(r)
        if hard_data.get("difficulty") != "hard":
            raise SystemExit("Expected hard difficulty")
        
        print(f"✓ Created hard practice session {hard_data['practiceId']}")
        
        # Test 6: Test invalid question number
        r, err = safe_call(
            client, "GET", f"{API}/v2/pronunciation/{practice_id}/audio/99", headers=headers
        )
        print_result("GET /api/v2/pronunciation/{id}/audio/99 (invalid)", r, err)
        
        if not r or r.status_code != 400:
            raise SystemExit(f"Expected 400 for invalid question number, got {r.status_code if r else 'no response'}")
        
        print("✓ Correctly rejected invalid question number")
        
        print("\n" + "="*50)
        print("✓ All pronunciation practice tests passed!")
        print("="*50 + "\n")


if __name__ == "__main__":
    main()

