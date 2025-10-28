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
        # token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImRhc2hhc2h1dG9zaDE5OTlAZ21haWwuY29tIiwiZW1haWwiOiJkYXNoYXNodXRvc2gxOTk5QGdtYWlsLmNvbSIsIm5hbWUiOiJBc2h1dG9zaCBEYXNoIiwiZXhwIjoxNzU4OTg3MDQ4LCJzdWIiOiJhY2Nlc3MifQ.VXejX1R4X0YBZrSBldwK_2enlAr0H6P9T3f2DCl9PHU"
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

        # Update profile (JSON)
        profile_data = {
            "degree": "B.Tech",
            "university": "Test Univ",
            "target_position": "javascript developer",
            "years_experience": 1.5,
        }
        r, err = safe_call(client, "PUT", f"{API}/users/profile", headers=headers, json=profile_data)
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
        r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "javascript developer", "difficulty": "easy"})
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
        r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "javascript developer"})
        print_result("POST /api/interviews/create (resume)", r, err)

        # List interviews (get current one id if missing)
        r, err = safe_call(client, "GET", f"{API}/interviews?limit=1", headers=headers)
        print_result("GET /api/interviews", r, err)
        lb = safe_json(r) if r else {}
        if not interview_id and isinstance(lb, dict) and lb.get("items"):
            interview_id = lb["items"][0].get("interviewId")

        # Test the new enhanced interviews endpoint (BEFORE summary report)
        r_enhanced, err_enhanced = safe_call(client, "GET", f"{API}/interviews-with-summary?limit=5", headers=headers)
        print_result("GET /api/interviews-with-summary (BEFORE summary)", r_enhanced, err_enhanced)
        if r_enhanced and r_enhanced.status_code == 200:
            enhanced_body = safe_json(r_enhanced)
            if isinstance(enhanced_body, dict):
                items = enhanced_body.get("items", [])
                print(f"   Found {len(items)} interviews (before summary generation)")
                for item in items[:2]:  # Show first 2 items
                    if isinstance(item, dict):
                        iid = item.get('interviewId', 'N/A')
                        track = item.get('track', 'N/A')
                        status = item.get('status', 'N/A')
                        kp = item.get('knowledgePercentage')
                        sp = item.get('speechFluencyPercentage')
                        available = item.get('summaryReportAvailable', False)
                        print(f"   - Interview {iid}: {track} ({status})")
                        print(f"     Knowledge: {kp}%, Speech: {sp}%, Available: {available}")
                        if available:
                            print(f"     Attempts: {item.get('attemptsCount', 0)}")
                            action_items = item.get('topActionItems', [])
                            if action_items:
                                print(f"     Top Actions: {', '.join(action_items[:2])}")  # Show first 2 action items

        # List questions for interview
        question_ids = []
        if interview_id:
            r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/questions?limit=5", headers=headers)  # Increased limit to ensure at least 3 questions
            print_result("GET /api/interviews/{id}/questions", r, err)
            qb = safe_json(r) if r else {}
            if isinstance(qb, dict) and qb.get("items"):
                items = qb["items"]
                if len(items) >= 3:
                    for i in [0, 2]:  # 1st and 3rd (0-indexed)
                        item = items[i]
                        if isinstance(item, dict):
                            qid = item.get("interviewQuestionId") or item.get("interview_question_id")
                            if qid:
                                question_ids.append(qid)

        # Create attempts for 1st and 3rd questions
        qa_ids = []
        if interview_id and question_ids:
            for qid in question_ids:
                attempt_payload = {"interviewId": interview_id, "questionId": qid}
                r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
                print_result(f"POST /api/interviews/question-attempts for question {qid}", r, err)
                ab = safe_json(r) if r else {}
                if isinstance(ab, dict):
                    qa_id = ab.get("questionAttemptId") or ab.get("question_attempt_id")
                    if qa_id:
                        qa_ids.append(qa_id)

        # List question attempts
        if interview_id:
            r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/question-attempts", headers=headers)
            print_result("GET /api/interviews/{id}/question-attempts", r, err)

        # Transcribe audio for each attempt if assets/Speech.mp3 exists
        speech_file_path = os.path.join("assets", "Speech.mp3")
        if os.path.exists(speech_file_path):
            for qa_id in qa_ids:
                with open(speech_file_path, "rb") as audio_file:
                    files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                    data = {"question_attempt_id": str(qa_id), "language": "en"}
                    r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=data)
                    print_result(f"POST /api/transcribe-whisper for attempt {qa_id}", r, err)

        # Complete analysis for each attempt (domain + communication + pace + pause)
        for qa_id in qa_ids:
            payload = {"question_attempt_id": qa_id, "analysis_types": ["domain", "communication", "pace", "pause"]}
            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=payload)
            print_result(f"POST /api/complete-analysis for attempt {qa_id}", r, err)

            # Individual analysis endpoints
            r, err = safe_call(client, "POST", f"{API}/domain-base-analysis", headers=headers, json={"question_attempt_id": qa_id})
            print_result(f"POST /api/domain-base-analysis for attempt {qa_id}", r, err)
            r, err = safe_call(client, "POST", f"{API}/communication-based-analysis", headers=headers, json={"question_attempt_id": qa_id})
            print_result(f"POST /api/communication-based-analysis for attempt {qa_id}", r, err)
            r, err = safe_call(client, "POST", f"{API}/analyze-pace", headers=headers, json={"question_attempt_id": qa_id})
            print_result(f"POST /api/analyze-pace for attempt {qa_id}", r, err)
            r, err = safe_call(client, "POST", f"{API}/analyze-pause", headers=headers, json={"question_attempt_id": qa_id})
            print_result(f"POST /api/analyze-pause for attempt {qa_id}", r, err)

        # Final report
        if interview_id:
            r, err = safe_call(client, "POST", f"{API}/final-report", headers=headers, json={"interviewId": interview_id})
            print_result("POST /api/final-report", r, err)
            r2, err2 = safe_call(client, "GET", f"{API}/final-report/{interview_id}", headers=headers)
            print_result("GET /api/final-report/{id}", r2, err2)

        # Summary report (independent from final-report)
        if interview_id:
            r, err = safe_call(client, "POST", f"{API}/summary-report", headers=headers, json={"interviewId": interview_id})
            print_result("POST /api/summary-report", r, err)
            if r and r.status_code == 200:
                # Verify track information is included in the response
                body = safe_json(r)
                if isinstance(body, dict):
                    track = body.get('track', 'N/A')
                    print(f"   Summary report generated for track: {track}")
                
                # Immediately fetch the persisted report
                rg, erg = safe_call(client, "GET", f"{API}/summary-report/{interview_id}", headers=headers)
                print_result("GET /api/summary-report/{id}", rg, erg)
                
                # Verify track information is also in the fetched report
                if rg and rg.status_code == 200:
                    body_fetch = safe_json(rg)
                    if isinstance(body_fetch, dict):
                        track_fetch = body_fetch.get('track', 'N/A')
                        print(f"   Fetched report track: {track_fetch}")
                
                # Test the new summary reports list endpoint
                rl, errl = safe_call(client, "GET", f"{API}/summary-reports?limit=5", headers=headers)
                print_result("GET /api/summary-reports", rl, errl)
                if rl and rl.status_code == 200:
                    body_list = safe_json(rl)
                    if isinstance(body_list, dict):
                        items = body_list.get("items", [])
                        print(f"   Found {len(items)} summary reports with full data")
                        for item in items[:2]:  # Show first 2 items
                            if isinstance(item, dict):
                                print(f"   - Interview {item.get('interview_id', 'N/A')}: {item.get('track', 'N/A')} ({item.get('difficulty', 'N/A')})")
                                report = item.get('report', {})
                                if isinstance(report, dict) and 'metrics' in report:
                                    report_track = report.get('track', 'N/A')
                                    print(f"     Full report data included with {len(report)} top-level fields, track: {report_track}")
                
                # AFTER summary report: Check interviews-with-summary again
                r_enhanced_after, err_enhanced_after = safe_call(client, "GET", f"{API}/interviews-with-summary?limit=5", headers=headers)
                print_result("GET /api/interviews-with-summary (AFTER summary)", r_enhanced_after, err_enhanced_after)
                if r_enhanced_after and r_enhanced_after.status_code == 200:
                    enhanced_body_after = safe_json(r_enhanced_after)
                    if isinstance(enhanced_body_after, dict):
                        items_after = enhanced_body_after.get("items", [])
                        print(f"   Found {len(items_after)} interviews (after summary generation)")
                        for item in items_after[:2]:  # Show first 2 items
                            if isinstance(item, dict):
                                iid = item.get('interviewId', 'N/A')
                                track = item.get('track', 'N/A')
                                status = item.get('status', 'N/A')
                                kp = item.get('knowledgePercentage')
                                sp = item.get('speechFluencyPercentage')
                                available = item.get('summaryReportAvailable', False)
                                attempts = item.get('attemptsCount', 0)
                                print(f"   - Interview {iid}: {track} ({status})")
                                print(f"     Knowledge: {kp}%, Speech: {sp}%")
                                print(f"     Summary Available: {available}, Attempts: {attempts}")
                                
                                # Verify data is now populated
                                if available and (kp is None or sp is None):
                                    print(f"   ⚠️  WARNING: Summary available but percentages are null!")
                                elif available and kp is not None and sp is not None:
                                    print(f"   ✅ Percentages successfully populated after summary generation!")
                                    
                                action_items = item.get('topActionItems', [])
                                if action_items:
                                    print(f"     Top {len(action_items)} action items: {', '.join(action_items[:2])}")
                                    print(f"   ✅ Action items successfully extracted!")
                                elif available:
                                    print(f"   ⚠️  WARNING: Summary available but no action items found!")
                
                # Verify interviews list now shows percentages after summary report generation
                r_check, err_check = safe_call(client, "GET", f"{API}/interviews?limit=1", headers=headers)
                print_result("GET /api/interviews (after summary)", r_check, err_check)
                if r_check and r_check.status_code == 200:
                    check_body = safe_json(r_check)
                    if isinstance(check_body, dict):
                        check_items = check_body.get("items", [])
                        if check_items:
                            first_item = check_items[0]
                            if isinstance(first_item, dict):
                                kp = first_item.get('knowledgePercentage')
                                sp = first_item.get('speechFluencyPercentage')
                                attempts = first_item.get('attemptsCount', 0)
                                print(f"   Interview {first_item.get('interviewId')} now shows:")
                                print(f"     Knowledge: {kp}%, Speech: {sp}%, Attempts: {attempts}")
                                if kp is None or sp is None:
                                    print(f"   ⚠️  WARNING: Percentages are null despite having {attempts} summary report(s)")
                                else:
                                    print(f"   ✅ Percentages successfully populated!")
                
                # Also check the enhanced endpoint (AFTER summary report)
                r_enh_check, err_enh_check = safe_call(client, "GET", f"{API}/interviews-with-summary?limit=1", headers=headers)
                print_result("GET /api/interviews-with-summary (AFTER summary)", r_enh_check, err_enh_check)
                if r_enh_check and r_enh_check.status_code == 200:
                    enh_check_body = safe_json(r_enh_check)
                    if isinstance(enh_check_body, dict):
                        enh_items = enh_check_body.get("items", [])
                        if enh_items:
                            enh_first = enh_items[0]
                            if isinstance(enh_first, dict):
                                kp_enh = enh_first.get('knowledgePercentage')
                                sp_enh = enh_first.get('speechFluencyPercentage')
                                available_enh = enh_first.get('summaryReportAvailable', False)
                                attempts_enh = enh_first.get('attemptsCount', 0)
                                actions = enh_first.get('topActionItems', [])
                                
                                print(f"   📊 Enhanced endpoint now shows:")
                                print(f"     - Summary Available: {available_enh}")
                                print(f"     - Knowledge: {kp_enh}%")
                                print(f"     - Speech: {sp_enh}%")
                                print(f"     - Attempts: {attempts_enh}")
                                print(f"     - Top {len(actions)} Action Items:")
                                for i, action in enumerate(actions[:3], 1):
                                    print(f"       {i}. {action}")
                                
                                # Validation
                                if not available_enh and attempts_enh > 0:
                                    print(f"   ⚠️  WARNING: summaryReportAvailable is False but attemptsCount is {attempts_enh}")
                                elif kp_enh is None or sp_enh is None:
                                    print(f"   ⚠️  WARNING: Enhanced endpoint percentages are null despite {attempts_enh} report(s)")
                                elif not actions and attempts_enh > 0:
                                    print(f"   ⚠️  WARNING: No action items despite having {attempts_enh} report(s)")
                                else:
                                    print(f"   ✅ Enhanced endpoint fully populated with all summary data!")

        # Test resume interview endpoint
        if interview_id:
            resume_payload = {"interview_id": interview_id}
            r_resume, err_resume = safe_call(client, "POST", f"{API}/interviews/resume", headers=headers, json=resume_payload)
            print_result("POST /api/interviews/resume", r_resume, err_resume)
            if r_resume and r_resume.status_code == 200:
                body_resume = safe_json(r_resume)
                if isinstance(body_resume, dict):
                    track_resume = body_resume.get('track', 'N/A')
                    total_questions = body_resume.get('total_questions', 0)
                    attempted_questions = body_resume.get('attempted_questions', 0)
                    remaining_questions = body_resume.get('remaining_questions', 0)
                    questions = body_resume.get('questions', [])
                    print(f"   Resume interview for track: {track_resume}")
                    print(f"   Total questions: {total_questions}, Attempted: {attempted_questions}, Remaining: {remaining_questions}")
                    print(f"   Questions without attempts: {len(questions)}")
                    if questions:
                        first_question = questions[0]
                        if isinstance(first_question, dict):
                            print(f"   First remaining question: {first_question.get('text', 'N/A')[:50]}...")


if __name__ == "__main__":
    main()
