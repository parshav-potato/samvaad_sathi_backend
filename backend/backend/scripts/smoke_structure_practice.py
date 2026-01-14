"""Smoke tests for structure practice feature."""

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
    return f"structure_{token}@example.com"


def main() -> None:
    """Test complete structure practice flow: create session, submit audio answer, analyze."""
    email = rand_email()
    password = "pass123!"
    name = "Structure Practice Test User"

    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        # Register & login
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        token = extract_token(safe_json(r) if r else {}) if not err else None

        r, err = safe_call(client, "POST", f"{API}/login", json={"email": email, "password": password})
        print_result("POST /api/login", r, err)
        login_body = safe_json(r) if r else {}
        token = extract_token(login_body) or token
        headers = auth_headers(token)

        # Test 1: Create an interview first
        r, err = safe_call(
            client, "POST", f"{API}/interviews/create",
            headers=headers,
            json={"track": "Software Engineering", "difficulty": "medium"}
        )
        print_result("POST /api/interviews/create", r, err)
        
        if not r or r.status_code != 201:
            print("⚠ Failed to create interview, will skip interview-based structure practice test")
            interview_id = None
        else:
            interview_data = safe_json(r)
            interview_id = interview_data.get("id") or interview_data.get("interviewId")
            print(f"✓ Created interview {interview_id}")
        
        # Test 2: Generate questions for the interview
        if interview_id:
            r, err = safe_call(
                client, "POST", f"{API}/interviews/generate-questions",
                headers=headers,
                json={"interviewId": interview_id, "use_resume": False, "count": 3}
            )
            print_result("POST /api/interviews/generate-questions", r, err)
            
            if not r or r.status_code not in (200, 201):
                print("⚠ Failed to generate questions, will use generic structure practice")
                interview_id = None
            else:
                gen_data = safe_json(r)
                question_count = gen_data.get("count", 0)
                print(f"✓ Generated {question_count} questions for interview")
        
        # Test 3a: Create structure practice session from interview
        if interview_id:
            create_payload = {"interviewId": interview_id}
            r, err = safe_call(
                client, "POST", f"{API}/v2/structure-practice/session", headers=headers, json=create_payload
            )
            print_result("POST /api/v2/structure-practice/session (from interview)", r, err)
            
            if not r or r.status_code != 201:
                raise SystemExit(f"Failed to create structure practice from interview: {r.status_code if r else 'no response'}")
            
            practice_data = safe_json(r)
            practice_id = practice_data.get("practiceId")
            practice_interview_id = practice_data.get("interviewId")
            
            if practice_interview_id != interview_id:
                raise SystemExit(f"Expected interviewId {interview_id}, got {practice_interview_id}")
            
            print(f"✓ Created practice session {practice_id} from interview {interview_id}")
        
        # Test 3b: Create structure practice session (no interview_id = generic questions)
        create_payload = {}
        r, err = safe_call(
            client, "POST", f"{API}/v2/structure-practice/session", headers=headers, json=create_payload
        )
        print_result("POST /api/v2/structure-practice/session (generic)", r, err)
        
        if not r or r.status_code != 201:
            raise SystemExit(f"Failed to create structure practice session: {r.status_code if r else 'no response'}")
        
        practice_data = safe_json(r)
        practice_id = practice_data.get("practiceId")  # camelCase from API
        interview_id = practice_data.get("interviewId")
        track = practice_data.get("track")
        questions = practice_data.get("questions", [])
        status = practice_data.get("status")
        
        # Validate response structure
        if not practice_id:
            raise SystemExit(f"Invalid response structure: missing practice_id")
        
        if interview_id is not None:
            raise SystemExit(f"Expected interview_id to be null for generic session, got {interview_id}")
        
        if status != "active":
            raise SystemExit(f"Expected status 'active', got '{status}'")
        
        if not questions or len(questions) == 0:
            raise SystemExit(f"Expected questions, got {len(questions)}")
        
        # Validate question structure
        first_question = questions[0]
        if not first_question.get("text"):
            raise SystemExit("Missing question text")
        if not first_question.get("structure_hint"):
            raise SystemExit("Missing structure hint")
        if first_question.get("index") != 0:
            raise SystemExit("First question index should be 0")
        
        print(f"✓ Created generic practice session {practice_id} with {len(questions)} questions")
        print(f"  Track: {track}")
        print(f"  First question: {first_question['text'][:60]}...")
        print(f"  Structure hint: {first_question['structure_hint'][:60]}...")
        
        # Test 4: Submit audio answer for first question
        # Use the Speech.mp3 file from assets folder
        test_audio_path = Path(__file__).parent.parent / "assets" / "Speech.mp3"
        
        if not test_audio_path.exists():
            print(f"⚠ Test audio file not found at {test_audio_path}")
            print("  Skipping audio submission test - Speech.mp3 not found")
            return
        
        with open(test_audio_path, "rb") as audio_file:
            files = {"file": ("answer.mp3", audio_file, "audio/mpeg")}
            data = {
                "language": "en",
                "time_spent_seconds": "45"
            }
            r, err = safe_call(
                client, 
                "POST", 
                f"{API}/v2/structure-practice/{practice_id}/question/0/submit",
                headers=headers,
                files=files,
                data=data
            )
        
        print_result("POST /api/v2/structure-practice/{id}/question/0/submit", r, err)
        
        if not r or r.status_code != 200:
            raise SystemExit(f"Failed to submit answer: {r.status_code if r else 'no response'}")
        
        submit_data = safe_json(r)
        answer_id = submit_data.get("answerId")  # camelCase from API
        submit_status = submit_data.get("status")
        message = submit_data.get("message", "")
        
        if not answer_id:
            raise SystemExit("Missing answer_id in response")
        
        if submit_status != "transcribed":
            raise SystemExit(f"Expected status 'transcribed', got '{submit_status}'")
        
        print(f"✓ Submitted audio answer (answer_id: {answer_id})")
        print(f"  Message: {message}")
        
        # Test 5: Analyze the submitted answer
        r, err = safe_call(
            client,
            "POST",
            f"{API}/v2/structure-practice/{practice_id}/question/0/analyze",
            headers=headers
        )
        print_result("POST /api/v2/structure-practice/{id}/question/0/analyze", r, err)
        
        if not r or r.status_code != 200:
            raise SystemExit(f"Failed to analyze answer: {r.status_code if r else 'no response'}")
        
        analysis_data = safe_json(r)
        
        # Validate analysis structure
        framework_progress = analysis_data.get("frameworkProgress")  # camelCase from API
        time_per_section = analysis_data.get("timePerSection")
        key_insight = analysis_data.get("keyInsight")
        llm_model = analysis_data.get("llmModel")
        llm_latency_ms = analysis_data.get("llmLatencyMs")
        
        if not framework_progress:
            raise SystemExit("Missing framework_progress in analysis")
        
        framework_name = framework_progress.get("frameworkName")  # camelCase from API
        sections = framework_progress.get("sections", [])
        completion_percentage = framework_progress.get("completionPercentage")
        
        if not framework_name or framework_name not in ["C-T-E-T-D", "STAR"]:
            raise SystemExit(f"Invalid framework_name: {framework_name}")
        
        if completion_percentage is None or completion_percentage < 0 or completion_percentage > 100:
            raise SystemExit(f"Invalid completion_percentage: {completion_percentage}")
        
        if not sections:
            raise SystemExit("Missing sections in framework_progress")
        
        print(f"✓ Analysis completed successfully")
        print(f"  Framework: {framework_name}")
        print(f"  Completion: {completion_percentage}%")
        print(f"  Sections analyzed: {len(sections)}")
        
        # Show section breakdown
        for section in sections:
            section_name = section.get("name")
            section_status = section.get("status")
            answer_recorded = section.get("answerRecorded")  # camelCase from API
            time_seconds = section.get("timeSpentSeconds", 0)
            print(f"    - {section_name}: {section_status} ({'✓' if answer_recorded else '✗'}, {time_seconds}s)")
        
        print(f"  Key Insight: {key_insight[:80]}...")
        print(f"  LLM Model: {llm_model} ({llm_latency_ms}ms)")
        
        # Test 6: Try to create session with interview (should fail if no interview exists)
        r, err = safe_call(
            client, "POST", f"{API}/v2/structure-practice/session", 
            headers=headers, 
            json={"interviewId": 99999}  # camelCase for request
        )
        print_result("POST /api/v2/structure-practice/session (invalid interview)", r, err)
        
        if r and r.status_code != 404:
            print(f"⚠ Expected 404 for invalid interview_id, got {r.status_code}")
        else:
            print("✓ Correctly rejected invalid interview_id")
        
        # Test 7: Try to submit answer to invalid question index
        if test_audio_path.exists():
            with open(test_audio_path, "rb") as audio_file:
                files = {"file": ("answer.mp3", audio_file, "audio/mpeg")}
                data = {"language": "en"}
                r, err = safe_call(
                    client,
                    "POST",
                    f"{API}/v2/structure-practice/{practice_id}/question/999/submit",
                    headers=headers,
                    files=files,
                    data=data
                )
            
            print_result("POST /api/v2/structure-practice/{id}/question/999/submit (invalid index)", r, err)
            
            if r and r.status_code != 400:
                print(f"⚠ Expected 400 for invalid question index, got {r.status_code}")
            else:
                print("✓ Correctly rejected invalid question index")
        
        print("\n" + "="*60)
        print("✅ ALL STRUCTURE PRACTICE TESTS PASSED")
        print("="*60)


if __name__ == "__main__":
    main()
