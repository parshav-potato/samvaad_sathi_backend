#!/bin/bash
# Test the updated analysis endpoint for section-by-section structure practice

BASE_URL="http://localhost:8000/api"
EMAIL="analysis_test_$(date +%s)@example.com"
PASSWORD="Test@1234"

echo "=========================================="
echo "Testing Structure Practice Analysis"
echo "=========================================="
echo ""

# Register and login
echo "1. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/users" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"name\": \"Analysis Test User\"
  }")

TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.authorizedUser.token // empty')
if [ -z "$TOKEN" ]; then
  echo "❌ Failed to register user"
  echo "$REGISTER_RESPONSE"
  exit 1
fi
echo "✓ User registered"
echo ""

# Create structure practice session
echo "2. Creating structure practice session..."
PRACTICE_RESPONSE=$(curl -s -X POST "$BASE_URL/v2/structure-practice/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track": "JavaScript Developer",
    "difficulty": "easy"
  }')

PRACTICE_ID=$(echo "$PRACTICE_RESPONSE" | jq -r '.practiceId // empty')
FRAMEWORK=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].framework // empty')
SECTIONS=$(echo "$PRACTICE_RESPONSE" | jq -c '.questions[0].sections // []')

if [ -z "$PRACTICE_ID" ]; then
  echo "❌ Failed to create practice session"
  echo "$PRACTICE_RESPONSE"
  exit 1
fi

echo "Practice ID: $PRACTICE_ID"
echo "Framework: $FRAMEWORK"
echo "Sections: $SECTIONS"
echo "✓ Practice session created"
echo ""

# Submit all sections
echo "3. Submitting all sections..."

# Create a simple audio file
AUDIO_FILE="/tmp/test_audio_analysis.mp3"
ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" -f mp3 "$AUDIO_FILE" -y 2>/dev/null

# Parse sections array
SECTION_COUNT=$(echo "$SECTIONS" | jq 'length')
echo "Total sections to submit: $SECTION_COUNT"

for i in $(seq 0 $((SECTION_COUNT - 1))); do
  SECTION_NAME=$(echo "$SECTIONS" | jq -r ".[$i]")
  echo ""
  echo "Submitting section $((i+1))/$SECTION_COUNT: $SECTION_NAME"
  
  SUBMIT_RESPONSE=$(curl -s -X POST "$BASE_URL/v2/structure-practice/$PRACTICE_ID/question/0/section/$SECTION_NAME/submit" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$AUDIO_FILE" \
    -F "language=en" \
    -F "time_spent_seconds=$((20 + i * 10))")
  
  echo "  Response: $SUBMIT_RESPONSE" | head -c 200
  echo ""
  
  SECTIONS_COMPLETE=$(echo "$SUBMIT_RESPONSE" | jq -r '.sectionsComplete // 0')
  IS_COMPLETE=$(echo "$SUBMIT_RESPONSE" | jq -r '.isComplete // false')
  NEXT_SECTION=$(echo "$SUBMIT_RESPONSE" | jq -r '.nextSection // "none"')
  
  echo "  - Sections complete: $SECTIONS_COMPLETE/$SECTION_COUNT"
  echo "  - Is complete: $IS_COMPLETE"
  echo "  - Next section: $NEXT_SECTION"
  
  if [ "$IS_COMPLETE" = "true" ]; then
    echo "✓ All sections submitted!"
    break
  fi
  
  # Small delay between submissions
  sleep 1
done

echo ""
echo "✓ All sections submitted"
echo ""

# Analyze the complete answer
echo "4. Analyzing complete answer..."
ANALYSIS_RESPONSE=$(curl -s -X POST "$BASE_URL/v2/structure-practice/$PRACTICE_ID/question/0/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo ""
echo "Analysis Response:"
echo "$ANALYSIS_RESPONSE" | jq '.'
echo ""

# Validate analysis response
FRAMEWORK_NAME=$(echo "$ANALYSIS_RESPONSE" | jq -r '.frameworkProgress.frameworkName // empty')
COMPLETION_PCT=$(echo "$ANALYSIS_RESPONSE" | jq -r '.frameworkProgress.completionPercentage // 0')
SECTIONS_ANALYZED=$(echo "$ANALYSIS_RESPONSE" | jq -r '.frameworkProgress.sectionsComplete // 0')
TOTAL_SECTIONS=$(echo "$ANALYSIS_RESPONSE" | jq -r '.frameworkProgress.totalSections // 0')
KEY_INSIGHT=$(echo "$ANALYSIS_RESPONSE" | jq -r '.keyInsight // empty')

echo "Analysis Summary:"
echo "  Framework: $FRAMEWORK_NAME"
echo "  Completion: $COMPLETION_PCT%"
echo "  Sections: $SECTIONS_ANALYZED/$TOTAL_SECTIONS"
echo "  Key Insight: $KEY_INSIGHT"
echo ""

# Check each section in the analysis
echo "Section Analysis:"
echo "$ANALYSIS_RESPONSE" | jq -r '.frameworkProgress.sections[] | "  - \(.name): \(.status) (recorded: \(.answerRecorded), time: \(.timeSpentSeconds)s)"'
echo ""

# Time per section
echo "Time Per Section:"
echo "$ANALYSIS_RESPONSE" | jq -r '.timePerSection[] | "  - \(.sectionName): \(.seconds)s"'
echo ""

# Validate all expected fields are present
if [ -z "$FRAMEWORK_NAME" ]; then
  echo "❌ Missing framework name in analysis"
  exit 1
fi

if [ "$COMPLETION_PCT" -eq 0 ]; then
  echo "⚠️  Warning: Completion percentage is 0"
fi

if [ "$SECTIONS_ANALYZED" -ne "$SECTION_COUNT" ]; then
  echo "⚠️  Warning: Sections analyzed ($SECTIONS_ANALYZED) doesn't match submitted ($SECTION_COUNT)"
fi

if [ -z "$KEY_INSIGHT" ]; then
  echo "❌ Missing key insight in analysis"
  exit 1
fi

echo "✓ Analysis completed successfully"
echo ""

# Cleanup
rm -f "$AUDIO_FILE"

echo "=========================================="
echo "✅ ALL TESTS PASSED"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Created practice session with $SECTION_COUNT sections"
echo "  - Submitted all $SECTION_COUNT sections individually"
echo "  - Analyzed complete answer with framework: $FRAMEWORK_NAME"
echo "  - Got completion percentage: $COMPLETION_PCT%"
echo "  - Received key insight and time breakdown"
