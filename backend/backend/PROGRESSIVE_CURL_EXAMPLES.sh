#!/bin/bash
# Progressive Section-by-Section Structure Practice - cURL Examples

BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "Section-by-Section Structure Practice"
echo "Progressive cURL Commands"
echo "=========================================="
echo ""

# ============================================
# STEP 1: Register and Login
# ============================================
echo "STEP 1: Register User"
echo "--------------------"
echo 'curl -X POST "'$BASE_URL'/users" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{'
echo '    "email": "test@example.com",'
echo '    "password": "Test@1234",'
echo '    "name": "Test User"'
echo '  }'"'"
echo ""
echo "# Save the token from response:"
echo '# TOKEN="<your_token_here>"'
echo ""
echo ""

# ============================================
# STEP 2: Create Structure Practice Session
# ============================================
echo "STEP 2: Create Structure Practice Session"
echo "--------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track": "JavaScript Developer",
    "difficulty": "easy"
  }'

# Response includes:
# - practiceId: (save this)
# - questions[0].framework: "STAR" or "C-T-E-T-D" or "GCDIO"
# - questions[0].sections: ["Situation", "Task", "Action", "Result"]
# - questions[0].current_section: "Situation"
# - questions[0].current_hint: "Start with Situation: Describe the context..."
EOF
echo ""
echo "# Save the practiceId from response:"
echo '# PRACTICE_ID="<practice_id_here>"'
echo ""
echo ""

# ============================================
# STEP 3: Submit Section 1 - Situation
# ============================================
echo "STEP 3: Submit First Section (Situation)"
echo "--------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Situation/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/situation_answer.mp3" \
  -F "language=en" \
  -F "time_spent_seconds=30"

# Response:
# {
#   "answerId": 1,
#   "practiceId": 9,
#   "questionIndex": 0,
#   "sectionName": "Situation",
#   "sectionsComplete": 1,
#   "totalSections": 4,
#   "nextSection": "Task",
#   "nextSectionHint": "Great start! Now move to Task. Define your responsibility...",
#   "isComplete": false,
#   "message": "Section 'Situation' recorded successfully (whisper-1, 5893ms). Continue to Task."
# }
EOF
echo ""
echo ""

# ============================================
# STEP 4: Submit Section 2 - Task
# ============================================
echo "STEP 4: Submit Second Section (Task)"
echo "--------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Task/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/task_answer.mp3" \
  -F "language=en" \
  -F "time_spent_seconds=25"

# Response:
# {
#   "sectionsComplete": 2,
#   "totalSections": 4,
#   "nextSection": "Action",
#   "nextSectionHint": "Good progress! Next is Action. Explain your actions...",
#   "isComplete": false
# }
EOF
echo ""
echo ""

# ============================================
# STEP 5: Submit Section 3 - Action
# ============================================
echo "STEP 5: Submit Third Section (Action)"
echo "--------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Action/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/action_answer.mp3" \
  -F "language=en" \
  -F "time_spent_seconds=45"

# Response:
# {
#   "sectionsComplete": 3,
#   "totalSections": 4,
#   "nextSection": "Result",
#   "nextSectionHint": "Almost done! Time for Result. Share the outcome...",
#   "isComplete": false
# }
EOF
echo ""
echo ""

# ============================================
# STEP 6: Submit Section 4 - Result (Final)
# ============================================
echo "STEP 6: Submit Final Section (Result)"
echo "--------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Result/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/result_answer.mp3" \
  -F "language=en" \
  -F "time_spent_seconds=20"

# Response:
# {
#   "sectionsComplete": 4,
#   "totalSections": 4,
#   "nextSection": null,
#   "nextSectionHint": null,
#   "isComplete": true,
#   "message": "Excellent! You've completed all sections of the STAR framework. Your answer will now be analyzed."
# }
EOF
echo ""
echo ""

# ============================================
# STEP 7: Analyze Complete Answer
# ============================================
echo "STEP 7: Analyze Complete Answer"
echo "--------------------"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Response:
# {
#   "frameworkProgress": {
#     "frameworkName": "STAR",
#     "sections": [
#       {
#         "name": "Situation",
#         "status": "complete",
#         "answerRecorded": true,
#         "timeSpentSeconds": 30
#       },
#       {
#         "name": "Task",
#         "status": "complete",
#         "answerRecorded": true,
#         "timeSpentSeconds": 25
#       },
#       {
#         "name": "Action",
#         "status": "complete",
#         "answerRecorded": true,
#         "timeSpentSeconds": 45
#       },
#       {
#         "name": "Result",
#         "status": "complete",
#         "answerRecorded": true,
#         "timeSpentSeconds": 20
#       }
#     ],
#     "completionPercentage": 95,
#     "sectionsComplete": 4,
#     "totalSections": 4,
#     "progressMessage": "Excellent work! All sections covered comprehensively."
#   },
#   "timePerSection": [...],
#   "keyInsight": "Strong STAR structure with clear situation, defined task, detailed actions, and measurable results.",
#   "llmModel": "gpt-5-chat-latest",
#   "llmLatencyMs": 4200
# }
EOF
echo ""
echo ""

# ============================================
# Framework-Specific Sections
# ============================================
echo "=========================================="
echo "Framework-Specific Sections"
echo "=========================================="
echo ""

echo "STAR Framework (Behavioral Questions):"
echo "  1. Situation"
echo "  2. Task"
echo "  3. Action"
echo "  4. Result"
echo ""

echo "C-T-E-T-D Framework (Technical Questions):"
echo "  1. Context"
echo "  2. Theory"
echo "  3. Example"
echo "  4. Trade-offs"
echo "  5. Decision"
echo ""

echo "GCDIO Framework (System Design):"
echo "  1. Goal"
echo "  2. Constraints"
echo "  3. Decision"
echo "  4. Implementation"
echo "  5. Outcome"
echo ""

# ============================================
# Error Examples
# ============================================
echo "=========================================="
echo "Error Handling Examples"
echo "=========================================="
echo ""

echo "Invalid Section Name:"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/InvalidSection/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3"

# Response (400):
# {
#   "detail": "Invalid section_name 'InvalidSection' for framework STAR. Valid sections: ['Situation', 'Task', 'Action', 'Result']"
# }
EOF
echo ""
echo ""

echo "Question Index Out of Range:"
cat << 'EOF'
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/99/section/Situation/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3"

# Response (400):
# {
#   "detail": "question_index 99 out of range for this practice session"
# }
EOF
echo ""
echo ""

# ============================================
# Complete Example with C-T-E-T-D
# ============================================
echo "=========================================="
echo "Complete C-T-E-T-D Example"
echo "=========================================="
echo ""

cat << 'EOF'
# For a technical question using C-T-E-T-D framework:

# Section 1: Context
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Context/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@context.mp3" \
  -F "time_spent_seconds=20"

# Section 2: Theory
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Theory/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@theory.mp3" \
  -F "time_spent_seconds=40"

# Section 3: Example
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Example/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@example.mp3" \
  -F "time_spent_seconds=50"

# Section 4: Trade-offs
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Trade-offs/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@tradeoffs.mp3" \
  -F "time_spent_seconds=35"

# Section 5: Decision
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/section/Decision/submit" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@decision.mp3" \
  -F "time_spent_seconds=15"

# Final Analysis
curl -X POST "http://localhost:8000/api/v2/structure-practice/$PRACTICE_ID/question/0/analyze" \
  -H "Authorization: Bearer $TOKEN"
EOF
echo ""
echo ""

echo "=========================================="
echo "Done! Use these commands as templates."
echo "=========================================="
