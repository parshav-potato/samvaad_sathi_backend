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

    with httpx.Client(base_url=BASE_URL, timeout=30.0) as client:
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

        # Test password change endpoint
        if token:
            r, err = safe_call(client, "PUT", f"{API}/users/password", headers=headers, json={"old_password": password, "new_password": "newpass123!"})
            print_result("PUT /api/users/password", r, err)
            
            # Try with wrong old password
            r, err = safe_call(client, "PUT", f"{API}/users/password", headers=headers, json={"old_password": "wrong", "new_password": "newpass123!"})
            print_result("PUT /api/users/password (wrong old)", r, err)

        # Test health endpoint
        r, err = safe_call(client, "GET", "/health")
        print_result("GET /health", r, err)

        # Negative: missing/invalid auth
        r, err = safe_call(client, "GET", f"{API}/me")
        print_result("GET /api/me (no auth)", r, err)
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers_invalid)
        print_result("GET /api/me (invalid token)", r, err)

        # Resume upload (requires auth)
        if token:
            # update user profiling attributes to user's table
            import os
            profile_attributes = {"degree":"xyz","university":"abc","target_position":"Data Science","years_experience":0}
            r,err = safe_call(client,"PUT",f"{API}/users/profile",headers=headers,json=profile_attributes)
            print_result(f"PUT {API}/users/profile",r,err)
            
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
            first_interview_response = safe_json(r) if r else {}
            first_interview_id = first_interview_response.get("id") if isinstance(first_interview_response, dict) else None
            
            # Repeat to verify resume path
            r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "data_science"})
            print_result("POST /api/interviews/create (resume)", r, err)

            # Test interview management endpoints
            if first_interview_id:
                # GET individual interview
                r, err = safe_call(client, "GET", f"{API}/interviews/{first_interview_id}", headers=headers)
                print_result("GET /api/interviews/{id}", r, err)
                
                # PUT update interview
                r, err = safe_call(client, "PUT", f"{API}/interviews/{first_interview_id}", headers=headers, json={"track": "ml_engineering", "difficulty": "medium"})
                print_result("PUT /api/interviews/{id}", r, err)

            # Interviews: generate questions (active fallback)
            r, err = safe_call(client, "POST", f"{API}/interviews/generate-questions", headers=headers)
            print_result("POST /api/interviews/generate-questions", r, err)

            # Interviews: generate questions for a specific interview id when known
            if first_interview_id:
                r, err = safe_call(
                    client,
                    "POST",
                    f"{API}/interviews/generate-questions",
                    headers=headers,
                    json={"interviewId": first_interview_id, "use_resume": True},
                )
                print_result("POST /api/interviews/generate-questions (with interviewId)", r, err)

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
                first_id = body["items"][0]["interviewId"]
                next_cursor = body.get("next_cursor")
                # Interviews: list questions for the first interview
                r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions?limit=2", headers=headers)
                print_result("GET /api/interviews/{id}/questions", r, err)
                qb = safe_json(r) if r else {}
                
                # Test individual question endpoints if questions exist
                if isinstance(qb, dict) and qb.get("items") and qb["items"]:
                    first_question = qb["items"][0]
                    if isinstance(first_question, dict) and "interviewQuestionId" in first_question:
                        question_id = first_question["interviewQuestionId"]
                        
                        # GET individual question
                        r, err = safe_call(client, "GET", f"{API}/interviews/{first_id}/questions/{question_id}", headers=headers)
                        print_result("GET /api/interviews/{id}/questions/{qid}", r, err)
                        
                        # DELETE individual question
                        r, err = safe_call(client, "DELETE", f"{API}/interviews/{first_id}/questions/{question_id}", headers=headers)
                        print_result("DELETE /api/interviews/{id}/questions/{qid}", r, err)
                
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
            
            # Test the new enhanced interviews endpoint
            try:
                r_enhanced, err_enhanced = safe_call(client, "GET", f"{API}/interviews-with-summary?limit=3", headers=headers)
                print_result("GET /api/interviews-with-summary", r_enhanced, err_enhanced)
                if r_enhanced and 200 <= r_enhanced.status_code < 300:
                    enhanced_body = safe_json(r_enhanced)
                    if isinstance(enhanced_body, dict):
                        items = enhanced_body.get("items", [])
                        print(f"   Found {len(items)} interviews with summary data")
                        for item in items[:2]:  # Show first 2 items
                            if isinstance(item, dict):
                                print(f"   - Interview {item.get('interview_id', 'N/A')}: {item.get('track', 'N/A')} ({item.get('status', 'N/A')})")
                                if item.get('summary_report_available'):
                                    print(f"     Knowledge: {item.get('knowledge_percentage', 'N/A')}%, Speech: {item.get('speech_fluency_percentage', 'N/A')}%")
                                    print(f"     Attempts: {item.get('attempts_count', 0)}")
                                    action_items = item.get('top_action_items', [])
                                    if action_items:
                                        print(f"     Top Actions: {', '.join(action_items[:2])}")  # Show first 2 action items
                                else:
                                    print(f"     No summary report available")
            except Exception as _e_enhanced:
                print_result("GET /api/interviews-with-summary", None, str(_e_enhanced))

            # Audio transcription: test with real speech file after creating questions
            # First, generate questions for the current active interview to create question attempts
            r, err = safe_call(
                client,
                "POST",
                f"{API}/interviews/generate-questions",
                headers=headers,
                json={"use_resume": True, "interviewId": current_interview_id} if 'current_interview_id' in locals() and current_interview_id else {"use_resume": True},
            )
            print_result("POST /api/interviews/generate-questions (fixed)", r, err)
            
            # Get the current active interview ID (should be the last one created)
            r, err = safe_call(client, "GET", f"{API}/interviews?limit=1", headers=headers)
            print_result("GET /api/interviews (current)", r, err)
            current_body = safe_json(r) if r else {}
            
            if isinstance(current_body, dict) and current_body.get("items"):
                current_interview_id = current_body["items"][0]["interviewId"]
                
                # Get the generated questions (InterviewQuestion objects)
                r, err = safe_call(client, "GET", f"{API}/interviews/{current_interview_id}/questions?limit=3", headers=headers)
                print_result("GET /api/interviews/{id}/questions (for attempts)", r, err)
                
                questions_response = safe_json(r) if r else {}
                if isinstance(questions_response, dict) and questions_response.get("items"):
                    # Create question attempts for the first few questions
                    first_question = questions_response["items"][0]
                    if isinstance(first_question, dict) and "interviewQuestionId" in first_question:
                        question_id = first_question["interviewQuestionId"]
                        
                        # Create a question attempt using the new endpoint (IDs in body)
                        attempt_payload = {"interviewId": current_interview_id, "questionId": question_id}
                        r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
                        print_result("POST /api/interviews/question-attempts", r, err)
                        
                        attempt_response = safe_json(r) if r else {}
                        if isinstance(attempt_response, dict) and "questionAttemptId" in attempt_response:
                            question_attempt_id = attempt_response["questionAttemptId"]
                            
                            # Test audio transcription with test_audio.mp3 file
                            import os
                            speech_file_path = os.path.join("scripts", "test_audio.mp3")
                            if os.path.exists(speech_file_path):
                                with open(speech_file_path, "rb") as audio_file:
                                    files_audio = {"file": ("test_audio.mp3", audio_file, "audio/mpeg")}
                                    audio_data = {"question_attempt_id": str(question_attempt_id), "language": "en"}
                                    r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=audio_data)
                                    print_result("POST /api/transcribe-whisper (test_audio)", r, err)
                            else:
                                print_result("POST /api/transcribe-whisper", None, "test_audio.mp3 file not found")
                        else:
                            print_result("Question attempt creation", None, "Failed to create question attempt")
                    else:
                        print_result("Question attempt creation", None, "No valid questions found to create attempts")
                
                # Also check the old question attempts endpoint (should still work for backward compatibility)
                r, err = safe_call(client, "GET", f"{API}/interviews/{current_interview_id}/question-attempts", headers=headers)
                print_result("GET /api/interviews/{id}/question-attempts (for audio)", r, err)
                
                questions_body = safe_json(r) if r else {}
                if isinstance(questions_body, dict) and questions_body.get("items"):
                    # Questions exist as QuestionAttempt objects with IDs! Get the first one
                    first_question_attempt = questions_body["items"][0]
                    
                    # Check if this is a question attempt object with an ID
                    if isinstance(first_question_attempt, dict) and "questionAttemptId" in first_question_attempt:
                        question_attempt_id = first_question_attempt["questionAttemptId"]
                        
                        # Test audio transcription with original Speech.mp3 file as fallback
                        import os
                        speech_file_path = os.path.join("assets", "Speech.mp3")
                        if os.path.exists(speech_file_path):
                            with open(speech_file_path, "rb") as audio_file:
                                files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                                audio_data = {"question_attempt_id": str(question_attempt_id), "language": "en"}
                                r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=audio_data)
                                print_result("POST /api/transcribe-whisper (fallback)", r, err)
                        else:
                            print_result("POST /api/transcribe-whisper", None, "Speech.mp3 file not found")
                    elif isinstance(first_question_attempt, str):
                        # Questions are returned as strings, not question attempt objects
                        # This means question attempts weren't created properly
                        print_result("POST /api/transcribe-whisper", None, "Question attempts not persisted as objects")
                else:
                    # No questions found, test with mock ID
                    import os
                    speech_file_path = os.path.join("assets", "Speech.mp3")
                    if os.path.exists(speech_file_path):
                        with open(speech_file_path, "rb") as audio_file:
                            files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                            audio_data = {"question_attempt_id": "1", "language": "en"}
                            r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=audio_data)
                            print_result("POST /api/transcribe-whisper (no questions)", r, err)
                    else:
                        print_result("POST /api/transcribe-whisper", None, "Speech.mp3 test file not found")

            # Additional comprehensive audio test - use question-attempts endpoint for correct question attempt IDs
            if isinstance(questions_body, dict) and questions_body.get("items"):
                print("\n--- Comprehensive Audio Transcription Test ---")
                import os
                speech_file_path = os.path.join("assets", "Speech.mp3")
                if os.path.exists(speech_file_path):
                    # First get question attempts to get proper IDs
                    qa_response, qa_err = safe_call(client, "GET", f"{API}/interviews/{current_interview_id}/question-attempts", headers=headers)
                    
                    if qa_response and 200 <= qa_response.status_code < 300:
                        qa_data = safe_json(qa_response)
                        if isinstance(qa_data, dict) and "items" in qa_data and qa_data["items"]:
                            qa_id = qa_data["items"][0]["questionAttemptId"]
                        else:
                            qa_id = 2  # Fallback
                    else:
                        qa_id = 2  # Fallback
                    
                    # Now test audio transcription with fresh file handle
                    with open(speech_file_path, "rb") as audio_file:
                        files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                        audio_data = {"question_attempt_id": str(qa_id), "language": "en"}
                        r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=audio_data)
                        print_result("POST /api/transcribe-whisper (comprehensive)", r, err)
                        
                        # Print detailed results if successful
                        if r and 200 <= r.status_code < 300:
                            resp_data = safe_json(r)
                            if isinstance(resp_data, dict):
                                print(f"   Filename: {resp_data.get('filename', 'N/A')}")
                                print(f"   Size: {resp_data.get('size', 'N/A')} bytes")
                                print(f"   Duration: {resp_data.get('durationSeconds', 'N/A')} seconds")
                                print(f"   Model: {resp_data.get('whisperModel', 'N/A')}")
                                print(f"   Latency: {resp_data.get('whisperLatencyMs', 'N/A')}ms")
                                print(f"   Saved: {resp_data.get('saved', False)}")
                else:
                    print_result("POST /api/transcribe-whisper (comprehensive)", None, "Speech.mp3 test file not found")

            # === ANALYSIS ENDPOINTS TESTS ===
            print("\n--- Analysis Endpoints Tests ---")
            # Ensure variables exist when earlier blocks were skipped
            current_interview_id = locals().get("current_interview_id")
            questions_body = locals().get("questions_body", {})

            # Test individual analysis endpoints with a transcribed question attempt
            if isinstance(questions_body, dict) and questions_body.get("items") and current_interview_id:
                qa_response, qa_err = safe_call(
                    client,
                    "GET",
                    f"{API}/interviews/{current_interview_id}/question-attempts",
                    headers=headers
                )

                if qa_response and 200 <= qa_response.status_code < 300:
                    qa_data = safe_json(qa_response)
                    if isinstance(qa_data, dict) and "items" in qa_data and qa_data["items"]:
                        # Find a question attempt with transcription
                        transcribed_qa_id = None
                        for qa_item in qa_data["items"]:
                            if isinstance(qa_item, dict) and qa_item.get("transcription"):
                                transcribed_qa_id = qa_item["questionAttemptId"]
                                break
                        
                        if transcribed_qa_id:
                            # Test individual analysis endpoints (new paths)
                            analysis_payload = {"question_attempt_id": transcribed_qa_id}
                            
                            # Test domain analysis (LLM-backed)
                            r, err = safe_call(client, "POST", f"{API}/domain-base-analysis", headers=headers, json=analysis_payload)
                            print_result("POST /api/domain-base-analysis", r, err)
                            
                            # Test communication analysis (LLM-backed)
                            r, err = safe_call(client, "POST", f"{API}/communication-based-analysis", headers=headers, json=analysis_payload)
                            print_result("POST /api/communication-based-analysis", r, err)
                            
                            # Test pace analysis
                            r, err = safe_call(client, "POST", f"{API}/analyze-pace", headers=headers, json=analysis_payload)
                            print_result("POST /api/analyze-pace", r, err)
                            
                            # Test pause analysis
                            r, err = safe_call(client, "POST", f"{API}/analyze-pause", headers=headers, json=analysis_payload)
                            print_result("POST /api/analyze-pause", r, err)
                            
                            # Test complete analysis - all types
                            complete_payload = {
                                "question_attempt_id": transcribed_qa_id,
                                "analysis_types": ["domain", "communication", "pace", "pause"]
                            }
                            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=complete_payload)
                            print_result("POST /api/complete-analysis (all types)", r, err)
                            
                            if r and 200 <= r.status_code < 300:
                                resp_data = safe_json(r)
                                if isinstance(resp_data, dict):
                                    print(f"   Analysis Complete: {resp_data.get('analysisComplete', 'N/A')}")
                                    print(f"   Total Latency: {resp_data.get('metadata', {}).get('totalLatencyMs', 'N/A')}ms")
                                    print(f"   Completed: {', '.join(resp_data.get('metadata', {}).get('completedAnalyses', []))}")
                                    print(f"   Failed: {', '.join(resp_data.get('metadata', {}).get('failedAnalyses', []))}")
                                    print(f"   Saved: {resp_data.get('saved', False)}")
                            
                            # Test complete analysis - partial types only
                            partial_payload = {
                                "question_attempt_id": transcribed_qa_id,
                                "analysis_types": ["domain", "pace"]
                            }
                            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=partial_payload)
                            print_result("POST /api/complete-analysis (partial types)", r, err)

                            # Communication analysis with override text to ensure endpoint works even when short
                            comm_override = {"question_attempt_id": transcribed_qa_id, "override_transcription": "I spoke at a moderate pace and structured my answer logically."}
                            r, err = safe_call(client, "POST", f"{API}/communication-based-analysis", headers=headers, json=comm_override)
                            print_result("POST /api/communication-based-analysis (override)", r, err)
                            
                        else:
                            # Test with mock question attempt ID if no transcribed data
                            mock_qa_id = qa_data["items"][0]["questionAttemptId"] if qa_data["items"] else 1
                            analysis_payload = {"question_attempt_id": mock_qa_id}
                            
                            # Updated: Should fail gracefully due to missing transcription
                            r, err = safe_call(client, "POST", f"{API}/domain-base-analysis", headers=headers, json=analysis_payload)
                            print_result("POST /api/domain-base-analysis (no transcription)", r, err)

                            # Provide override_transcription to succeed even without stored transcription
                            analysis_payload_override = {"question_attempt_id": mock_qa_id, "override_transcription": "This is a short answer about data structures and algorithms."}
                            r, err = safe_call(client, "POST", f"{API}/domain-base-analysis", headers=headers, json=analysis_payload_override)
                            print_result("POST /api/domain-base-analysis (override transcription)", r, err)
                            
                            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json={
                                "question_attempt_id": mock_qa_id,
                                "analysis_types": ["domain"]
                            })
                            print_result("POST /api/complete-analysis (no transcription)", r, err)
                            
            # Test analysis authentication errors
            print("\n--- Analysis Authentication Tests ---")
            bad_headers = {"Authorization": "Bearer invalid_token"}
            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=bad_headers, json={
                "question_attempt_id": 1,
                "analysis_types": ["domain"]
            })
            print_result("POST /api/complete-analysis (invalid token)", r, err)
            
            # Test analysis with no authentication
            r, err = safe_call(client, "POST", f"{API}/complete-analysis", json={
                "question_attempt_id": 1, 
                "analysis_types": ["domain"]
            })
            print_result("POST /api/complete-analysis (no auth)", r, err)
            
            # Test analysis with invalid analysis types
            if headers:  # Valid auth token
                r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json={
                    "question_attempt_id": 1,
                    "analysis_types": ["invalid_type", "also_invalid"]
                })
                print_result("POST /api/complete-analysis (invalid types)", r, err)
                
                # Test analysis with non-existent question attempt
                r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json={
                    "question_attempt_id": 99999,
                    "analysis_types": ["domain"]
                })
                print_result("POST /api/complete-analysis (non-existent QA)", r, err)

            # Interviews: complete session (explicit interview_id)
            if 'current_interview_id' in locals() and current_interview_id:
                r, err = safe_call(client, "POST", f"{API}/interviews/complete", headers=headers, json={"interviewId": current_interview_id})
                print_result("POST /api/interviews/complete", r, err)

            # Test DELETE interview (at the end after all other tests)
            if first_interview_id:
                r, err = safe_call(client, "DELETE", f"{API}/interviews/{first_interview_id}", headers=headers)
                print_result("DELETE /api/interviews/{id}", r, err)

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

        # Final report generation (if we have a current interview id)
        try:
            if 'current_interview_id' in locals() and current_interview_id:
                payload = {"interviewId": current_interview_id}
                r, err = safe_call(client, "POST", f"{API}/final-report", headers=headers, json=payload)
                print_result("POST /api/final-report", r, err)
                # quick checks
                if r and 200 <= r.status_code < 300:
                    body = safe_json(r)
                    if isinstance(body, dict):
                        for k in ("interviewId", "summary", "knowledgeCompetence", "speechStructureFluency", "overallScore", "saved"):
                            if k not in body:
                                print(f"   WARN: final-report missing key: {k}")
                        if body.get("saved") is not True:
                            print("   WARN: final-report not persisted (saved != true)")

                    # Verify retrieval of saved report via GET endpoint
                    r2, err2 = safe_call(client, "GET", f"{API}/final-report/{current_interview_id}", headers=headers)
                    print_result("GET /api/final-report/{id}", r2, err2)
                    if r2 and 200 <= r2.status_code < 300:
                        body2 = safe_json(r2)
                        if isinstance(body2, dict):
                            for k in ("interviewId", "summary", "knowledgeCompetence", "speechStructureFluency", "overallScore"):
                                if k not in body2:
                                    print(f"   WARN: final-report (GET) missing key: {k}")
                # New: summary report generation (independent from final report)
                try:
                    sr_payload = {"interviewId": current_interview_id}
                    r3, err3 = safe_call(client, "POST", f"{API}/summary-report", headers=headers, json=sr_payload)
                    print_result("POST /api/summary-report", r3, err3)
                    if r3 and 200 <= r3.status_code < 300:
                        body3 = safe_json(r3)
                        if isinstance(body3, dict):
                            for k in ("interviewId", "metrics", "strengths", "areasOfImprovement", "actionableInsights"):
                                if k not in body3:
                                    print(f"   WARN: summary-report missing key: {k}")
                            # Light sanity: show averages if present
                            try:
                                metrics = (body3.get("metrics", {}) or {})
                                kc = metrics.get("knowledgeCompetence", {}) or {}
                                ssf = metrics.get("speechStructure", {}) or {}
                                print(f"   KC avg (5pt): {kc.get('average5pt', 'N/A')}, %: {kc.get('averagePct', 'N/A')}")
                                print(f"   SSF avg (5pt): {ssf.get('average5pt', 'N/A')}, %: {ssf.get('averagePct', 'N/A')}")
                            except Exception:
                                pass
                except Exception as _e3:
                    print_result("POST /api/summary-report", None, str(_e3))
                
                # Test the new summary reports list endpoint
                try:
                    rl, errl = safe_call(client, "GET", f"{API}/summary-reports?limit=3", headers=headers)
                    print_result("GET /api/summary-reports", rl, errl)
                    if rl and 200 <= rl.status_code < 300:
                        body_list = safe_json(rl)
                        if isinstance(body_list, dict):
                            items = body_list.get("items", [])
                            print(f"   Found {len(items)} summary reports")
                            for item in items[:2]:  # Show first 2 items
                                if isinstance(item, dict):
                                    print(f"   - Interview {item.get('interview_id', 'N/A')}: {item.get('track', 'N/A')} ({item.get('difficulty', 'N/A')})")
                                    # Show report details if available
                                    report = item.get('report', {})
                                    if isinstance(report, dict):
                                        metrics = report.get('metrics', {})
                                        if metrics:
                                            kc = metrics.get('knowledgeCompetence', {})
                                            ss = metrics.get('speechStructure', {})
                                            print(f"     KC: {kc.get('averagePct', 'N/A')}%, SS: {ss.get('averagePct', 'N/A')}%")
                except Exception as _e4:
                    print_result("GET /api/summary-reports", None, str(_e4))
        except Exception as _e:
            print_result("POST /api/final-report", None, str(_e))

        # Clean up (end of tests)
        print("\n" + "="*50 + " SMOKE TEST COMPLETE " + "="*50)


if __name__ == "__main__":
    main()
