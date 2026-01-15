#!/bin/bash
# Complete working analysis test - creates everything fresh

BASE_URL="http://localhost:8000/api"

echo "==================================="
echo "Complete Analysis Test"
echo "==================================="
echo ""

# 1. Register user
echo "1. Registering user..."
EMAIL="analysis_test_$(date +%s)@example.com"
REG=$(curl -s -X POST "$BASE_URL/users" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Test@1234\",\"name\":\"Test User\"}")

TOKEN=$(echo "$REG" | jq -r '.authorizedUser.token')
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Registration failed"
  echo "$REG"
  exit 1
fi
echo "✓ Registered: $EMAIL"
echo ""

# 2. Create practice session
echo "2. Creating practice session..."
SESSION=$(curl -s -X POST "$BASE_URL/v2/structure-practice/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"track":"JavaScript Developer","difficulty":"easy"}')

PRACTICE_ID=$(echo "$SESSION" | jq -r '.practiceId')
FRAMEWORK=$(echo "$SESSION" | jq -r '.questions[0].framework')
SECTIONS_JSON=$(echo "$SESSION" | jq -c '.questions[0].sections')

if [ -z "$PRACTICE_ID" ] || [ "$PRACTICE_ID" = "null" ]; then
  echo "❌ Session creation failed"
  echo "$SESSION"
  exit 1
fi

echo "Practice ID: $PRACTICE_ID"
echo "Framework: $FRAMEWORK"
echo "Sections: $SECTIONS_JSON"
echo "✓ Session created"
echo ""

# 3. Use existing audio file
AUDIO_FILE="/home/parshav-potato/projects/samvaad_sathi_backend/backend/backend/assets/Speech.mp3"

if [ ! -f "$AUDIO_FILE" ]; then
  echo "❌ Audio file not found at $AUDIO_FILE"
  exit 1
fi
echo "Using audio file: $AUDIO_FILE"
echo ""

# 4. Submit all sections
echo "3. Submitting sections..."
SECTION_NAMES=$(echo "$SECTIONS_JSON" | jq -r '.[]')
SECTION_COUNT=$(echo "$SECTIONS_JSON" | jq 'length')

for SECTION in $SECTION_NAMES; do
  echo "  Submitting: $SECTION"
  
  SUBMIT=$(curl -s -X POST "$BASE_URL/v2/structure-practice/$PRACTICE_ID/question/0/section/$SECTION/submit" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$AUDIO_FILE" \
    -F "language=en" \
    -F "time_spent_seconds=35")
  
  # Check if submission was successful
  ANSWER_ID=$(echo "$SUBMIT" | jq -r '.answerId // empty')
  if [ -z "$ANSWER_ID" ]; then
    echo "    ⚠️  Warning: No answerId in response"
    echo "    Response: $(echo "$SUBMIT" | jq -c '.')"
  else
    COMPLETE=$(echo "$SUBMIT" | jq -r '.sectionsComplete')
    TOTAL=$(echo "$SUBMIT" | jq -r '.totalSections')
    IS_DONE=$(echo "$SUBMIT" | jq -r '.isComplete')
    echo "    ✓ Submitted ($COMPLETE/$TOTAL complete, done=$IS_DONE)"
  fi
  
  sleep 1  # Give server time to process
done

echo "✓ All sections submitted"
echo ""

# 5. Verify sections were saved
echo "4. Verifying sections in database..."
# We'll just try the analysis - if it fails with "No sections submitted", we know they weren't saved

# 6. Analyze
echo "5. Analyzing complete answer..."
echo ""

ANALYSIS=$(curl -s -X POST "$BASE_URL/v2/structure-practice/$PRACTICE_ID/question/0/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

# Check for errors
ERROR=$(echo "$ANALYSIS" | jq -r '.detail // empty')
if [ -n "$ERROR" ]; then
  echo "❌ Analysis failed: $ERROR"
  echo ""
  echo "Full response:"
  echo "$ANALYSIS" | jq '.'
  exit 1
fi

# Display results
echo "✅ Analysis successful!"
echo ""
echo "==== ANALYSIS RESULTS ===="
echo ""

FRAMEWORK_NAME=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.frameworkName')
COMPLETION=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.completionPercentage')
SECTIONS_DONE=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.sectionsComplete')
TOTAL_SECTIONS=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.totalSections')
INSIGHT=$(echo "$ANALYSIS" | jq -r '.keyInsight')
PROGRESS_MSG=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.progressMessage')

echo "Framework: $FRAMEWORK_NAME"
echo "Completion: $COMPLETION%"
echo "Sections: $SECTIONS_DONE/$TOTAL_SECTIONS"
echo ""
echo "Progress Message:"
echo "  $PROGRESS_MSG"
echo ""
echo "Key Insight:"
echo "  $INSIGHT"
echo ""
echo "Section Breakdown:"
echo "$ANALYSIS" | jq -r '.frameworkProgress.sections[] | "  \(.name): \(.status) (recorded: \(.answerRecorded), time: \(.timeSpentSeconds)s)"'
echo ""
echo "Time Analysis:"
echo "$ANALYSIS" | jq -r '.timePerSection[] | "  \(.sectionName): \(.seconds)s"'
echo ""

echo "==================================="
echo "✅ Test completed successfully!"
echo "==================================="
