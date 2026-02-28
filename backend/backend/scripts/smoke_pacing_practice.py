"""Smoke tests for speech pacing practice feature.

Covers:
  1.  GET  /api/pacing-practice/levels  (fresh user — all locked except level 1)
  2.  POST /api/pacing-practice/session  (level 1 — success)
  3.  POST /api/pacing-practice/session  (level 2 — locked, expect 403)
  4.  POST /api/pacing-practice/session  (level 3 — locked, expect 403)
  5.  POST /api/pacing-practice/session/{id}/submit  (audio upload + analysis)
  6.  GET  /api/pacing-practice/session/{id}  (fetch completed session)
  7.  POST /api/pacing-practice/session/{id}/submit  (replay — expect 409)
  8.  GET  /api/pacing-practice/levels  (after completion — readiness > 0)
  9.  GET  /api/pacing-practice/levels  (without auth — expect 403/401)
  10. GET  /api/pacing-practice/session/{id}  (other user — expect 404)
  11. POST /api/pacing-practice/session  (invalid level — expect 422)
"""

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

PACING_API = f"{API}/pacing-practice"


def rand_email(prefix: str = "pacing") -> str:
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{prefix}_{token}@example.com"


def _register_and_login(client: httpx.Client, email: str, password: str, name: str) -> str | None:
    """Register a user, log in, and return the JWT token."""
    r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
    print_result("POST /api/users", r, err)
    token = extract_token(safe_json(r) if r else {})

    r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
    print_result("POST /api/login", r, err)
    if r:
        token = extract_token(safe_json(r)) or token
    return token


def main() -> None:
    """Run all pacing practice smoke tests."""
    password = "pass123!"

    # Audio file used for submission (same one used by structure practice smoke tests)
    audio_path = Path(__file__).parent.parent / "assets" / "Speech.mp3"
    if not audio_path.exists():
        # Fallback to the scripts-adjacent test_audio.mp3
        audio_path = Path(__file__).parent / "test_audio.mp3"
    if not audio_path.exists():
        print(f"⚠  No test audio file found – skipping audio-submission tests")
        audio_path = None

    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        # ------------------------------------------------------------------ #
        # User A – primary test user                                          #
        # ------------------------------------------------------------------ #
        email_a = rand_email("pacing_a")
        token_a = _register_and_login(client, email_a, password, "Pacing Test UserA")
        if not token_a:
            raise SystemExit("Could not obtain auth token for primary user")
        headers_a = auth_headers(token_a)

        # ------------------------------------------------------------------ #
        # Test 1: GET /levels – fresh user, all locked except level 1         #
        # ------------------------------------------------------------------ #
        r, err = safe_call(client, "GET", f"{PACING_API}/levels", headers=headers_a)
        print_result("GET /api/pacing-practice/levels (fresh user)", r, err)
        if not r or r.status_code != 200:
            raise SystemExit(f"[Test 1] Expected 200, got {r.status_code if r else 'no response'}")

        levels_data = safe_json(r)
        levels = levels_data.get("levels", [])
        overall_readiness = levels_data.get("overallReadiness", -1)

        if len(levels) != 3:
            raise SystemExit(f"[Test 1] Expected 3 levels, got {len(levels)}")
        if overall_readiness != 0:
            raise SystemExit(f"[Test 1] Expected overallReadiness=0 for fresh user, got {overall_readiness}")

        level_map = {lv["level"]: lv for lv in levels}
        if level_map[1]["status"] not in ("in_progress", "complete"):
            raise SystemExit(f"[Test 1] Level 1 should be unlocked, got status={level_map[1]['status']}")
        if level_map[2]["status"] != "locked":
            raise SystemExit(f"[Test 1] Level 2 should be locked, got status={level_map[2]['status']}")
        if level_map[3]["status"] != "locked":
            raise SystemExit(f"[Test 1] Level 3 should be locked, got status={level_map[3]['status']}")
        print(f"✓ [Test 1] Levels correct – L1 unlocked, L2+L3 locked, readiness={overall_readiness}%")

        # ------------------------------------------------------------------ #
        # Test 2: POST /session – level 1 (should succeed)                    #
        # ------------------------------------------------------------------ #
        r, err = safe_call(client, "POST", f"{PACING_API}/session", headers=headers_a, json={"level": 1})
        print_result("POST /api/pacing-practice/session (level 1)", r, err)
        if not r or r.status_code != 201:
            raise SystemExit(f"[Test 2] Expected 201, got {r.status_code if r else 'no response'}")

        session_data = safe_json(r)
        session_id = session_data.get("sessionId")
        prompt_text = session_data.get("promptText", "")
        level_name = session_data.get("levelName", "")
        status = session_data.get("status", "")
        level_returned = session_data.get("level")

        if not session_id:
            raise SystemExit("[Test 2] Missing sessionId in response")
        if not prompt_text:
            raise SystemExit("[Test 2] Missing promptText in response")
        if level_returned != 1:
            raise SystemExit(f"[Test 2] Expected level=1, got {level_returned}")
        if status != "pending":
            raise SystemExit(f"[Test 2] Expected status='pending', got '{status}'")
        if "Level 1" not in level_name:
            raise SystemExit(f"[Test 2] Unexpected levelName: '{level_name}'")
        print(f"✓ [Test 2] Created session {session_id}, prompt: {prompt_text[:60]}...")

        # ------------------------------------------------------------------ #
        # Test 3: POST /session – level 2 while locked (expect 403)           #
        # ------------------------------------------------------------------ #
        r, err = safe_call(client, "POST", f"{PACING_API}/session", headers=headers_a, json={"level": 2})
        print_result("POST /api/pacing-practice/session (level 2 locked)", r, err)
        if not r or r.status_code != 403:
            raise SystemExit(f"[Test 3] Expected 403 for locked level 2, got {r.status_code if r else 'no response'}")
        print("✓ [Test 3] Locked level 2 correctly rejected with 403")

        # ------------------------------------------------------------------ #
        # Test 4: POST /session – level 3 while locked (expect 403)           #
        # ------------------------------------------------------------------ #
        r, err = safe_call(client, "POST", f"{PACING_API}/session", headers=headers_a, json={"level": 3})
        print_result("POST /api/pacing-practice/session (level 3 locked)", r, err)
        if not r or r.status_code != 403:
            raise SystemExit(f"[Test 4] Expected 403 for locked level 3, got {r.status_code if r else 'no response'}")
        print("✓ [Test 4] Locked level 3 correctly rejected with 403")

        # ------------------------------------------------------------------ #
        # Test 5: POST /session/{id}/submit – audio upload + analysis         #
        # ------------------------------------------------------------------ #
        if audio_path:
            with open(audio_path, "rb") as af:
                files = {"file": ("answer.mp3", af, "audio/mpeg")}
                r, err = safe_call(
                    client,
                    "POST",
                    f"{PACING_API}/session/{session_id}/submit",
                    headers=headers_a,
                    files=files,
                )
            print_result(f"POST /api/pacing-practice/session/{session_id}/submit", r, err)
            if not r or r.status_code != 200:
                raise SystemExit(f"[Test 5] Expected 200, got {r.status_code if r else 'no response'}: {safe_json(r) if r else ''}")

            submit_data = safe_json(r)
            score = submit_data.get("score")
            score_label = submit_data.get("scoreLabel", "")
            speech_speed = submit_data.get("speechSpeed", {})
            pause_dist = submit_data.get("pauseDistribution", {})
            returned_level = submit_data.get("level")
            returned_session_id = submit_data.get("sessionId")

            if score is None or not (0 <= score <= 100):
                raise SystemExit(f"[Test 5] score out of range or missing: {score}")
            if not score_label:
                raise SystemExit("[Test 5] Missing scoreLabel")
            if returned_level != 1:
                raise SystemExit(f"[Test 5] Expected level=1, got {returned_level}")
            if returned_session_id != session_id:
                raise SystemExit(f"[Test 5] Session ID mismatch: {returned_session_id} != {session_id}")

            # Validate speechSpeed structure
            for key in ("value", "idealRange", "status", "feedback"):
                if key not in speech_speed:
                    raise SystemExit(f"[Test 5] Missing '{key}' in speechSpeed")
            if speech_speed["idealRange"] != "120-150":
                raise SystemExit(f"[Test 5] Unexpected idealRange for speechSpeed: {speech_speed['idealRange']}")
            if speech_speed["status"] not in ("Good", "Needs Adjustment"):
                raise SystemExit(f"[Test 5] Unexpected status in speechSpeed: {speech_speed['status']}")

            # Validate pauseDistribution structure
            for key in ("value", "idealRange", "status", "feedback"):
                if key not in pause_dist:
                    raise SystemExit(f"[Test 5] Missing '{key}' in pauseDistribution")
            if pause_dist["idealRange"] != "8-12 words":
                raise SystemExit(f"[Test 5] Unexpected idealRange for pauseDistribution: {pause_dist['idealRange']}")

            wpm_val = speech_speed["value"]
            pause_val = pause_dist["value"]
            print(f"✓ [Test 5] Score={score}/100 ({score_label}), WPM={wpm_val}, Pause interval={pause_val}")
            print(f"  Speech speed: {speech_speed['status']} – {speech_speed['feedback']}")
            print(f"  Pause dist:   {pause_dist['status']} – {pause_dist['feedback']}")
        else:
            print("⚠  [Test 5] Skipped – no audio file available")
            score = None

        # ------------------------------------------------------------------ #
        # Test 6: GET /session/{id} – fetch completed session                 #
        # ------------------------------------------------------------------ #
        if audio_path:
            r, err = safe_call(client, "GET", f"{PACING_API}/session/{session_id}", headers=headers_a)
            print_result(f"GET /api/pacing-practice/session/{session_id}", r, err)
            if not r or r.status_code != 200:
                raise SystemExit(f"[Test 6] Expected 200, got {r.status_code if r else 'no response'}")

            detail = safe_json(r)
            detail_status = detail.get("status")
            detail_score = detail.get("score")
            detail_transcript = detail.get("transcript")
            detail_level = detail.get("level")
            detail_prompt = detail.get("promptText", "")

            if detail_status != "completed":
                raise SystemExit(f"[Test 6] Expected status='completed', got '{detail_status}'")
            if detail_score != score:
                raise SystemExit(f"[Test 6] Score mismatch: detail={detail_score}, submit={score}")
            if not detail_transcript:
                raise SystemExit("[Test 6] Missing transcript in session detail")
            if detail_level != 1:
                raise SystemExit(f"[Test 6] Expected level=1, got {detail_level}")
            if not detail_prompt:
                raise SystemExit("[Test 6] Missing promptText in session detail")

            speech_speed_detail = detail.get("speechSpeed")
            pause_dist_detail = detail.get("pauseDistribution")
            if speech_speed_detail is None:
                raise SystemExit("[Test 6] Missing speechSpeed in completed session detail")
            if pause_dist_detail is None:
                raise SystemExit("[Test 6] Missing pauseDistribution in completed session detail")

            print(f"✓ [Test 6] Session detail correct – status=completed, score={detail_score}, transcript present")

        # ------------------------------------------------------------------ #
        # Test 7: POST /session/{id}/submit – replay (expect 409)             #
        # ------------------------------------------------------------------ #
        if audio_path:
            with open(audio_path, "rb") as af:
                files = {"file": ("answer.mp3", af, "audio/mpeg")}
                r, err = safe_call(
                    client,
                    "POST",
                    f"{PACING_API}/session/{session_id}/submit",
                    headers=headers_a,
                    files=files,
                )
            print_result(f"POST /api/pacing-practice/session/{session_id}/submit (replay)", r, err)
            if not r or r.status_code != 409:
                raise SystemExit(f"[Test 7] Expected 409 for duplicate submit, got {r.status_code if r else 'no response'}")
            print("✓ [Test 7] Duplicate submission correctly rejected with 409")

        # ------------------------------------------------------------------ #
        # Test 8: GET /levels – after at least one completed session          #
        # ------------------------------------------------------------------ #
        if audio_path:
            r, err = safe_call(client, "GET", f"{PACING_API}/levels", headers=headers_a)
            print_result("GET /api/pacing-practice/levels (after attempt)", r, err)
            if not r or r.status_code != 200:
                raise SystemExit(f"[Test 8] Expected 200, got {r.status_code if r else 'no response'}")

            levels_data = safe_json(r)
            readiness_after = levels_data.get("overallReadiness", -1)
            levels_after = {lv["level"]: lv for lv in levels_data.get("levels", [])}

            # Level 1 should now have a best_score set
            best_l1 = levels_after[1].get("bestScore")
            if best_l1 is None:
                raise SystemExit(f"[Test 8] Level 1 bestScore should be set after submission")
            if best_l1 != score:
                raise SystemExit(f"[Test 8] Level 1 bestScore={best_l1} doesn't match submitted score={score}")
            if readiness_after <= 0:
                raise SystemExit(f"[Test 8] overallReadiness should be > 0 after a submission, got {readiness_after}")

            print(f"✓ [Test 8] Readiness updated: {readiness_after}%, Level 1 best={best_l1}")

        # ------------------------------------------------------------------ #
        # Test 9: GET /levels – without auth (expect 401/403)                 #
        # ------------------------------------------------------------------ #
        r, err = safe_call(client, "GET", f"{PACING_API}/levels")
        print_result("GET /api/pacing-practice/levels (no auth)", r, err)
        if not r or r.status_code not in (401, 403):
            raise SystemExit(f"[Test 9] Expected 401/403 without auth, got {r.status_code if r else 'no response'}")
        print(f"✓ [Test 9] Unauthenticated request correctly rejected with {r.status_code}")

        # ------------------------------------------------------------------ #
        # Test 10: GET /session/{id} – other user's session (expect 404)      #
        # ------------------------------------------------------------------ #
        email_b = rand_email("pacing_b")
        token_b = _register_and_login(client, email_b, password, "Pacing Test UserB")
        if token_b and audio_path:
            headers_b = auth_headers(token_b)
            r, err = safe_call(client, "GET", f"{PACING_API}/session/{session_id}", headers=headers_b)
            print_result(f"GET /api/pacing-practice/session/{session_id} (other user)", r, err)
            if not r or r.status_code != 404:
                raise SystemExit(f"[Test 10] Expected 404 for session owned by another user, got {r.status_code if r else 'no response'}")
            print("✓ [Test 10] Cross-user session correctly rejected with 404")
        else:
            print("⚠  [Test 10] Skipped – could not register second user or no audio")

        # ------------------------------------------------------------------ #
        # Test 11: POST /session – invalid level (expect 422)                 #
        # ------------------------------------------------------------------ #
        r, err = safe_call(client, "POST", f"{PACING_API}/session", headers=headers_a, json={"level": 5})
        print_result("POST /api/pacing-practice/session (level=5 invalid)", r, err)
        if not r or r.status_code != 422:
            raise SystemExit(f"[Test 11] Expected 422 for level=5, got {r.status_code if r else 'no response'}")
        print("✓ [Test 11] Invalid level=5 correctly rejected with 422")

        # ------------------------------------------------------------------ #
        # Done                                                                #
        # ------------------------------------------------------------------ #
        print()
        print("=" * 60)
        print("✅  ALL PACING PRACTICE SMOKE TESTS PASSED")
        print("=" * 60)


if __name__ == "__main__":
    main()
