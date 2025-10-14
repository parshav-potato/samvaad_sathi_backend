import os
import random
import string

import httpx

from scripts.smoke_utils import BASE_URL, API, safe_call, print_result, safe_json, extract_token, auth_headers


def rand_str(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def main() -> None:
    """
    Smoke test for re-attempt scenarios:
    1. Create interview with 5 questions
    2. Answer questions 1, 2, 3 in first session
    3. Generate summary report (should show 3 questions)
    4. Re-attempt questions 1, 2 (leave empty), answer question 4
    5. Generate new summary report
    6. Verify: Should show questions 3 and 4 only (latest valid attempts)
    """
    email = f"reattempt_{rand_str()}@example.com"
    password = "pass123!"
    name = "ReAttempt User"

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # Register & Login
        r, err = safe_call(client, "POST", f"{API}/users", json={"email": email, "password": password, "name": name})
        print_result("POST /api/users", r, err)
        body = safe_json(r) if r else {}
        token = extract_token(body) if isinstance(body, dict) else None
        headers = auth_headers(token)

        # Upload resume
        profile_data = {
            "degree": "B.Tech",
            "university": "Test Univ",
            "target_position": "react developer",
            "years_experience": 2,
        }
        r, err = safe_call(client, "PUT", f"{API}/users/profile", headers=headers, json=profile_data)
        print_result("PUT /api/users/profile", r, err)

        files_txt = {"file": ("sample.txt", b"React developer with Redux experience", "text/plain")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=files_txt)
        print_result("POST /api/extract-resume", r, err)

        # Create interview
        r, err = safe_call(client, "POST", f"{API}/interviews/create", headers=headers, json={"track": "react developer", "difficulty": "medium"})
        print_result("POST /api/interviews/create", r, err)
        interview_id = None
        b = safe_json(r) if r else {}
        if isinstance(b, dict):
            interview_id = b.get("id") or b.get("interviewId") or b.get("interview_id")

        if not interview_id:
            print("❌ Failed to create interview")
            return

        # Generate 5 questions
        gen_payload = {"use_resume": True, "interviewId": interview_id}
        r, err = safe_call(client, "POST", f"{API}/interviews/generate-questions", headers=headers, json=gen_payload)
        print_result("POST /api/interviews/generate-questions", r, err)

        # Get all question IDs
        r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/questions?limit=10", headers=headers)
        print_result("GET /api/interviews/{id}/questions", r, err)
        
        question_ids = []
        qb = safe_json(r) if r else {}
        if isinstance(qb, dict) and qb.get("items"):
            for item in qb["items"]:
                if isinstance(item, dict):
                    qid = item.get("interviewQuestionId") or item.get("interview_question_id")
                    if qid:
                        question_ids.append(qid)

        if len(question_ids) < 5:
            print(f"❌ Expected 5 questions, got {len(question_ids)}")
            return

        print(f"\n✅ Got {len(question_ids)} questions: {question_ids}\n")

        # ========== SESSION 1: Answer Q1, Q2, Q3 ==========
        print("\n" + "="*60)
        print("SESSION 1: Answering questions 1, 2, 3")
        print("="*60 + "\n")

        session1_qa_ids = []
        speech_file_path = os.path.join("assets", "Speech.mp3")
        
        if not os.path.exists(speech_file_path):
            print(f"❌ Audio file not found: {speech_file_path}")
            return

        # Answer first 3 questions
        for idx in [0, 1, 2]:
            qid = question_ids[idx]
            
            # Create attempt
            attempt_payload = {"interviewId": interview_id, "questionId": qid}
            r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
            print_result(f"POST /api/interviews/question-attempts for Q{idx+1} (id={qid})", r, err)
            
            ab = safe_json(r) if r else {}
            qa_id = None
            if isinstance(ab, dict):
                qa_id = ab.get("questionAttemptId") or ab.get("question_attempt_id")
                if qa_id:
                    session1_qa_ids.append(qa_id)

            if not qa_id:
                print(f"❌ Failed to create attempt for Q{idx+1}")
                continue

            # Transcribe audio
            with open(speech_file_path, "rb") as audio_file:
                files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                data = {"question_attempt_id": str(qa_id), "language": "en"}
                r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=data)
                print_result(f"POST /api/transcribe-whisper for Q{idx+1}", r, err)

            # Complete analysis
            payload = {"question_attempt_id": qa_id, "analysis_types": ["domain", "communication", "pace", "pause"]}
            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=payload)
            print_result(f"POST /api/complete-analysis for Q{idx+1}", r, err)

        # Generate first summary report
        print("\n" + "-"*60)
        print("Generating FIRST summary report (should show 3 questions)")
        print("-"*60 + "\n")

        r, err = safe_call(client, "POST", f"{API}/summary-report", headers=headers, json={"interviewId": interview_id})
        print_result("POST /api/summary-report (Session 1)", r, err)
        
        if r and r.status_code == 200:
            body = safe_json(r)
            if isinstance(body, dict):
                qa = body.get('questionAnalysis', [])
                score_summary = body.get('scoreSummary', {})
                kc = score_summary.get('knowledgeCompetence', {})
                ssf = score_summary.get('speechAndStructure', {})
                
                print(f"\n📊 First Report Summary:")
                print(f"   Questions in report: {len(qa)}")
                print(f"   Knowledge: {kc.get('percentage', 0)}%")
                print(f"   Speech: {ssf.get('percentage', 0)}%")
                
                if len(qa) != 5:
                    print(f"   ⚠️  Expected 5 questions (3 answered + 2 unanswered), got {len(qa)}")
                else:
                    # Count how many have feedback
                    answered = sum(1 for q in qa if q.get('feedback') is not None)
                    print(f"   ✅ All 5 questions present: {answered} with answers, {5-answered} without")

        # ========== SESSION 2: Re-attempt Q1, Q2 (empty), Answer Q4 ==========
        print("\n" + "="*60)
        print("SESSION 2: Re-attempting Q1, Q2 (empty), answering Q4")
        print("="*60 + "\n")

        session2_qa_ids = []

        # Re-attempt Q1 and Q2 but DON'T transcribe or analyze (leave empty)
        for idx in [0, 1]:
            qid = question_ids[idx]
            
            attempt_payload = {"interviewId": interview_id, "questionId": qid}
            r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
            print_result(f"POST /api/interviews/question-attempts for Q{idx+1} RE-ATTEMPT (EMPTY)", r, err)
            
            ab = safe_json(r) if r else {}
            if isinstance(ab, dict):
                qa_id = ab.get("questionAttemptId") or ab.get("question_attempt_id")
                if qa_id:
                    session2_qa_ids.append(qa_id)
                    print(f"   ⚠️  Created empty attempt for Q{idx+1} (no transcription/analysis)")

        # Answer Q4 (index 3) with full transcription and analysis
        qid_4 = question_ids[3]
        attempt_payload = {"interviewId": interview_id, "questionId": qid_4}
        r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
        print_result(f"POST /api/interviews/question-attempts for Q4 (id={qid_4})", r, err)
        
        ab = safe_json(r) if r else {}
        qa_id_4 = None
        if isinstance(ab, dict):
            qa_id_4 = ab.get("questionAttemptId") or ab.get("question_attempt_id")
            if qa_id_4:
                session2_qa_ids.append(qa_id_4)

        if qa_id_4:
            # Transcribe audio for Q4
            with open(speech_file_path, "rb") as audio_file:
                files_audio = {"file": ("Speech.mp3", audio_file, "audio/mpeg")}
                data = {"question_attempt_id": str(qa_id_4), "language": "en"}
                r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, files=files_audio, data=data)
                print_result(f"POST /api/transcribe-whisper for Q4", r, err)

            # Complete analysis for Q4
            payload = {"question_attempt_id": qa_id_4, "analysis_types": ["domain", "communication", "pace", "pause"]}
            r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=payload)
            print_result(f"POST /api/complete-analysis for Q4", r, err)

        # Generate second summary report
        print("\n" + "-"*60)
        print("Generating SECOND summary report")
        print("Expected: Q3 and Q4 with feedback (Q1, Q2 re-attempts were empty)")
        print("-"*60 + "\n")

        r, err = safe_call(client, "POST", f"{API}/summary-report", headers=headers, json={"interviewId": interview_id})
        print_result("POST /api/summary-report (Session 2)", r, err)
        
        if r and r.status_code == 200:
            body = safe_json(r)
            if isinstance(body, dict):
                qa = body.get('questionAnalysis', [])
                score_summary = body.get('scoreSummary', {})
                kc = score_summary.get('knowledgeCompetence', {})
                ssf = score_summary.get('speechAndStructure', {})
                
                print(f"\n📊 Second Report Summary:")
                print(f"   Questions in report: {len(qa)}")
                print(f"   Knowledge: {kc.get('percentage', 0)}%")
                print(f"   Speech: {ssf.get('percentage', 0)}%")
                
                # Should show all 5 questions
                if len(qa) != 5:
                    print(f"   ❌ Expected 5 questions total, got {len(qa)}")
                else:
                    print(f"   ✅ All 5 questions present in report")
                
                # Check which questions have feedback
                questions_with_feedback = []
                questions_without_feedback = []
                
                for q in qa:
                    qnum = q.get('id')
                    feedback = q.get('feedback')
                    if feedback is not None:
                        questions_with_feedback.append(qnum)
                    else:
                        questions_without_feedback.append(qnum)
                
                print(f"\n   Questions WITH feedback: {sorted(questions_with_feedback)}")
                print(f"   Questions WITHOUT feedback: {sorted(questions_without_feedback)}")
                
                # Expected: Q3 (index 3) and Q4 (index 4) should have feedback
                # Q1, Q2 were overwritten with empty attempts, Q5 never attempted
                expected_with = {3, 4}
                expected_without = {1, 2, 5}
                
                actual_with = set(questions_with_feedback)
                actual_without = set(questions_without_feedback)
                
                if actual_with == expected_with and actual_without == expected_without:
                    print(f"\n   ✅ RE-ATTEMPT TEST PASSED!")
                    print(f"      - Q1, Q2: Empty re-attempts correctly excluded from feedback")
                    print(f"      - Q3: First session answer preserved (not re-attempted)")
                    print(f"      - Q4: New answer in session 2 included")
                    print(f"      - Q5: Never attempted, correctly has no feedback")
                else:
                    print(f"\n   ❌ RE-ATTEMPT TEST FAILED!")
                    print(f"      Expected with feedback: {expected_with}, got: {actual_with}")
                    print(f"      Expected without feedback: {expected_without}, got: {actual_without}")
                
                # Verify scoring makes sense (2/5 questions = max 40%)
                kc_pct = kc.get('percentage', 0)
                ssf_pct = ssf.get('percentage', 0)
                
                if kc_pct > 40 or ssf_pct > 40:
                    print(f"\n   ⚠️  WARNING: Scores exceed 40% (2/5 questions):")
                    print(f"      Knowledge: {kc_pct}%, Speech: {ssf_pct}%")
                else:
                    print(f"\n   ✅ Scores appropriately capped (2/5 questions = max 40%)")

        # List all question attempts to verify
        print("\n" + "-"*60)
        print("All question attempts for this interview:")
        print("-"*60 + "\n")
        
        r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/question-attempts", headers=headers)
        print_result("GET /api/interviews/{id}/question-attempts", r, err)
        
        if r and r.status_code == 200:
            body = safe_json(r)
            if isinstance(body, dict):
                items = body.get('items', [])
                print(f"\n   Total attempts in database: {len(items)}")
                
                # Group by question_id
                attempts_by_q = {}
                for item in items:
                    if isinstance(item, dict):
                        q_id = item.get('questionId') or item.get('question_id')
                        if q_id:
                            if q_id not in attempts_by_q:
                                attempts_by_q[q_id] = []
                            attempts_by_q[q_id].append(item)
                
                for q_id, attempts in sorted(attempts_by_q.items()):
                    q_idx = question_ids.index(q_id) + 1 if q_id in question_ids else '?'
                    print(f"\n   Question {q_idx} (id={q_id}): {len(attempts)} attempt(s)")
                    for i, att in enumerate(attempts, 1):
                        has_trans = bool(att.get('transcription'))
                        has_analysis = bool(att.get('analysisJson') or att.get('analysis_json'))
                        att_id = att.get('questionAttemptId') or att.get('id')
                        print(f"      Attempt {i} (id={att_id}): Transcription={has_trans}, Analysis={has_analysis}")


if __name__ == "__main__":
    main()
