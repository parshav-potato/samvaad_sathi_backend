"""
Smoke test for the interviews v2 workflow with follow-up questions.

This script mirrors the original smoke golden path but targets the new /api/v2
endpoints that generate 5 questions and produce adaptive follow-ups for two
of the prompts. It verifies that:
  * Interviews can be created via /api/v2 routes.
  * Question generation returns 5 items with follow-up metadata.
  * Creating an attempt and uploading audio triggers follow-up generation.
  * Follow-up questions are persisted and exposed through the standard
    /api/interviews/{id}/questions endpoint.
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

AUDIO_SAMPLE = Path(__file__).resolve().parent.parent / "assets" / "Speech.mp3"

ALLOWED_SUPPLEMENT_TYPES = {"code", "diagram"}
MERMAID_STARTERS = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "classDiagram")


def rand_email() -> str:
    token = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"v2_{token}@example.com"


def _validate_supplement(supp: dict) -> None:
    stype = str(supp.get("supplementType") or supp.get("supplement_type") or "").lower()
    fmt = str(supp.get("format") or "").lower()
    content = str(supp.get("content") or "")

    if stype not in ALLOWED_SUPPLEMENT_TYPES:
        raise SystemExit(f"Supplement type invalid: {stype}")

    if stype == "diagram":
        if fmt != "mermaid":
            raise SystemExit(f"Diagram supplement missing mermaid format: {fmt}")
        stripped = content.strip()
        if "```mermaid" in stripped:
            return
        if not any(stripped.startswith(prefix) for prefix in MERMAID_STARTERS):
            raise SystemExit(f"Mermaid content does not start with a known directive: {stripped[:40]}")
def main() -> None:
    email = rand_email()
    password = "pass123!"
    name = "V2 Follow Up User"

    if not AUDIO_SAMPLE.exists():
        raise SystemExit(f"Audio sample not found at {AUDIO_SAMPLE}")
    audio_bytes = AUDIO_SAMPLE.read_bytes()

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

        # Basic profile setup
        r, err = safe_call(client, "GET", f"{API}/me", headers=headers)
        print_result("GET /api/me", r, err)
        profile_payload = {
            "degree": "B.Tech",
            "university": "Smoke Test U",
            "target_position": "javascript developer",
            "years_experience": 2.5,
        }
        r, err = safe_call(client, "PUT", f"{API}/users/profile", headers=headers, json=profile_payload)
        print_result("PUT /api/users/profile", r, err)

        # Upload a simple resume file
        resume_files = {"file": ("sample.txt", b"follow up smoke test resume", "text/plain")}
        r, err = safe_call(client, "POST", f"{API}/extract-resume", headers=headers, files=resume_files)
        print_result("POST /api/extract-resume", r, err)

        # Create interview via v2 endpoint
        create_payload = {"track": "javascript developer", "difficulty": "medium"}
        r, err = safe_call(client, "POST", f"{API}/v2/interviews/create", headers=headers, json=create_payload)
        print_result("POST /api/v2/interviews/create", r, err)
        body = safe_json(r) if r else {}
        interview_id = body.get("interview_id") or body.get("interviewId")
        if not interview_id:
            raise SystemExit("Failed to create interview via v2 endpoint")

        # Generate 5 questions
        gen_payload = {"interviewId": interview_id, "useResume": True}
        r, err = safe_call(client, "POST", f"{API}/v2/interviews/generate-questions", headers=headers, json=gen_payload)
        print_result("POST /api/v2/interviews/generate-questions", r, err)
        gen_body = safe_json(r) if r else {}
        if not isinstance(gen_body, dict):
            raise SystemExit(f"Question generation returned non-JSON body: {gen_body}")
        items = gen_body.get("items") or []
        follow_up_ready = [item for item in items if item.get("followUpStrategy")]
        supplements_present = [item for item in items if item.get("supplement")]
        print(json.dumps({
            "name": "follow-up-metadata",
            "total_questions": len(items),
            "follow_up_ready": len(follow_up_ready),
            "supplements_with_items": len(supplements_present),
        }))
        if len(items) != 5 or len(follow_up_ready) < 2:
            raise SystemExit("V2 question generation did not return expected follow-up metadata")
        if len(supplements_present) != len(items):
            raise SystemExit("Supplements were not returned inline with generated questions")
        # Validate supplement structure/types
        for itm in supplements_present:
            _validate_supplement(itm.get("supplement") or {})

        target_question = follow_up_ready[0]
        question_id = target_question.get("interviewQuestionId")
        if not question_id:
            raise SystemExit("Unable to resolve questionId for follow-up-ready question")

        # Create attempt for the follow-up-ready question
        attempt_payload = {"interviewId": interview_id, "questionId": question_id}
        r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
        print_result("POST /api/interviews/question-attempts", r, err)
        attempt_body = safe_json(r) if r else {}
        question_attempt_id = attempt_body.get("question_attempt_id") or attempt_body.get("questionAttemptId")
        if not question_attempt_id:
            raise SystemExit("Failed to create question attempt for follow-up question")

        # Upload audio answer to trigger Whisper + follow-up generation
        data = {"question_attempt_id": str(question_attempt_id), "language": "en"}
        files = {"file": (AUDIO_SAMPLE.name, audio_bytes, "audio/mpeg")}
        r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, data=data, files=files)
        print_result("POST /api/transcribe-whisper (v2 follow-up)", r, err)
        transcribe_body = safe_json(r) if r else {}
        follow_up_generated = bool(transcribe_body.get("follow_up_generated") or transcribe_body.get("followUpGenerated"))
        follow_up_question = transcribe_body.get("follow_up_question") or transcribe_body.get("followUpQuestion")
        if not follow_up_generated or not follow_up_question:
            raise SystemExit("Follow-up was not returned inline with transcription response")
        follow_up_qid_inline = follow_up_question.get("interview_question_id") or follow_up_question.get("interviewQuestionId")
        follow_up_attempt_id_inline = follow_up_question.get("question_attempt_id") or follow_up_question.get("questionAttemptId")
        if not follow_up_qid_inline or not follow_up_attempt_id_inline:
            raise SystemExit(f"Follow-up payload missing ids: {follow_up_question}")
        print(json.dumps({
            "name": "follow-up-inline",
            "question_id": follow_up_qid_inline,
            "attempt_id": follow_up_attempt_id_inline,
            "strategy": follow_up_question.get("strategy"),
        }))

        # Fetch questions to confirm follow-up persistence
        r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/questions?limit=20", headers=headers)
        print_result("GET /api/interviews/{id}/questions (v2)", r, err)
        question_list = safe_json(r) if r else {}
        question_items = question_list.get("items", []) if isinstance(question_list, dict) else []
        follow_up_questions = [
            q for q in question_items
            if q.get("is_follow_up") or q.get("isFollowUp")
        ]
        supplements_from_get = [q for q in question_items if q.get("supplement")]
        if question_items and len(supplements_from_get) != len(question_items):
            raise SystemExit("Supplements were not included on the first questions fetch")
        for supp_wrapped in supplements_from_get:
            _validate_supplement(supp_wrapped.get("supplement") or {})
        print(json.dumps({
            "name": "follow-up-verification",
            "follow_ups_found": len(follow_up_questions),
            "parent_question_id": follow_up_questions[0].get("parent_question_id") if follow_up_questions else None,
        }))

        if not follow_up_questions:
            raise SystemExit("No follow-up questions were found after transcription; validation failed.")

        # ---------------------------------------------------------------------
        # NEW: Verify answering the follow-up question and getting analysis
        # ---------------------------------------------------------------------
        
        # 1. Identify the newly created follow-up question
        follow_up_q = follow_up_questions[0]
        follow_up_qid = follow_up_qid_inline or follow_up_q.get("interviewQuestionId") or follow_up_q.get("interview_question_id")
        if not follow_up_qid:
            raise SystemExit("Follow-up question ID not found")
        if follow_up_qid_inline and follow_up_qid_inline != follow_up_qid:
            print(f"   ⚠️ Follow-up question id mismatch (inline {follow_up_qid_inline} vs list {follow_up_qid})")
            
        print(f"   Targeting follow-up question ID: {follow_up_qid}")

        # 2. Create an attempt for this follow-up question
        # Note: The system might have auto-created an attempt (check service logic), 
        # but the standard flow allows creating one if needed. 
        # Let's check if an attempt already exists or create a new one.
        # The FollowUpService.handle_transcription_saved actually creates the attempt!
        # "follow_up_attempt = await self._question_attempt_repo.create_attempt(...)"
        
        # Let's find the attempt for this question
        r, err = safe_call(client, "GET", f"{API}/interviews/{interview_id}/question-attempts", headers=headers)
        print_result("GET /api/interviews/{id}/question-attempts", r, err)
        attempts_body = safe_json(r) if r else {}
        attempts_list = attempts_body.get("items", [])
        
        follow_up_attempt_id = follow_up_attempt_id_inline
        for att in attempts_list:
            if att.get("questionId") == follow_up_qid:
                follow_up_attempt_id = att.get("questionAttemptId")
                break
        
        if not follow_up_attempt_id:
            print("   Follow-up attempt not found in list, creating one manually...")
            attempt_payload = {"interviewId": interview_id, "questionId": follow_up_qid}
            r, err = safe_call(client, "POST", f"{API}/interviews/question-attempts", headers=headers, json=attempt_payload)
            print_result("POST /api/interviews/question-attempts (follow-up)", r, err)
            ab = safe_json(r) if r else {}
            follow_up_attempt_id = ab.get("questionAttemptId")

        if not follow_up_attempt_id:
            raise SystemExit("Failed to get attempt ID for follow-up question")

        print(f"   Using Follow-up Attempt ID: {follow_up_attempt_id}")

        # 3. Upload audio for the follow-up attempt (Answer the follow-up)
        # We use the same audio sample for simplicity
        data_fu = {"question_attempt_id": str(follow_up_attempt_id), "language": "en"}
        files_fu = {"file": (AUDIO_SAMPLE.name, audio_bytes, "audio/mpeg")}
        r, err = safe_call(client, "POST", f"{API}/transcribe-whisper", headers=headers, data=data_fu, files=files_fu)
        print_result("POST /api/transcribe-whisper (answering follow-up)", r, err)
        
        # Verify NO new follow-up is generated (chain should stop or be limited)
        # The logic only triggers if strategy is set. Follow-up questions usually don't have a strategy set 
        # unless explicitly configured. The generated follow-up likely has strategy=None.
        fu_transcribe_body = safe_json(r) if r else {}
        if fu_transcribe_body.get("follow_up_generated"):
            print("   ℹ️  Note: Another follow-up was generated (recursive follow-ups?).")
        else:
            print("   ✅ Correct: No further follow-up generated for this answer.")

        # 4. Trigger Analysis for the follow-up answer
        # We'll run the complete analysis
        analysis_payload = {
            "question_attempt_id": follow_up_attempt_id, 
            "analysis_types": ["domain", "communication", "pace", "pause"]
        }
        r, err = safe_call(client, "POST", f"{API}/complete-analysis", headers=headers, json=analysis_payload)
        print_result("POST /api/complete-analysis (follow-up)", r, err)
        
        if not r or r.status_code != 200:
             raise SystemExit("Analysis failed for follow-up attempt")
             
        analysis_body = safe_json(r)
        if not analysis_body.get("analysis_complete"):
            print(f"   ⚠️  Analysis incomplete: {analysis_body.get('message')}")
        else:
            print("   ✅ Analysis completed successfully for follow-up.")
             
        # Verify analysis content exists
        agg = analysis_body.get("aggregated_analysis", {})
        domain = agg.get("domain", {})
        comm = agg.get("communication", {})
        
        # Debug print
        print(f"   DEBUG: Full Analysis Body: {json.dumps(analysis_body, indent=2)}")
        
        print(f"   Analysis Results - Domain Score: {domain.get('domain_score')}, Comm Score: {comm.get('communication_score')}")
        if domain.get("domain_score") is not None:
            print("   ✅ Domain analysis present")
        if comm.get("communication_score") is not None:
            print("   ✅ Communication analysis present")

        # ---------------------------------------------------------------------
        # NEW: Generate Summary Report and Verify Scores
        # ---------------------------------------------------------------------
        print("\n   Generating Summary Report...")
        r, err = safe_call(client, "POST", f"{API}/summary-report", headers=headers, json={"interviewId": interview_id})
        print_result("POST /api/summary-report", r, err)
        
        if not r or r.status_code != 200:
             print("   ⚠️  Summary report generation failed")
        else:
             report_body = safe_json(r)
             # V2 report structure check
             score_summary = report_body.get("scoreSummary", {})
             kc = score_summary.get("knowledgeCompetence", {})
             ss = score_summary.get("speechAndStructure", {})
             
             print(f"   Summary Report Scores:")
             print(f"     - Knowledge Competence: {kc.get('score')}/{kc.get('maxScore')} ({kc.get('percentage')}%)")
             print(f"     - Speech & Structure: {ss.get('score')}/{ss.get('maxScore')} ({ss.get('percentage')}%)")
             
             if kc.get("score") is not None and ss.get("score") is not None:
                 print("   ✅ Summary report scores populated successfully.")
             else:
                 print("   ⚠️  Summary report scores are missing or null.")
                 print(f"   DEBUG: Full Report: {json.dumps(report_body, indent=2)}")
if __name__ == "__main__":
    main()
