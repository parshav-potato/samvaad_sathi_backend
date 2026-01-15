#!/bin/bash
# Complete analysis test - register, create session, submit all sections, analyze

BASE_URL="http://localhost:8000/api"
EMAIL="analyze_$(date +%s)@example.com"

echo "=========================================="
echo "Complete Structure Practice Analysis Test"
echo "=========================================="
echo ""

# Register
echo "1. Registering..."
REG_RESPONSE=$(curl -s -X POST "$BASE_URL/users" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"Test@1234\",\"name\":\"Test User\"}")
TOKEN=$(echo "$REG_RESPONSE" | jq -r '.authorizedUser.token')
echo "✓ Registered"
echo ""

# Create session
echo "2. Creating practice session..."
PRACTICE_RESPONSE=$(curl -s -X POST "$BASE_URL/v2/structure-practice/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"track":"JavaScript Developer","difficulty":"easy"}')
PRACTICE_ID=$(echo "$PRACTICE_RESPONSE" | jq -r '.practiceId')
FRAMEWORK=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].framework')
SECTIONS=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].sections[]')

echo "Practice ID: $PRACTICE_ID"
echo "Framework: $FRAMEWORK"
echo "✓ Session created"
echo ""

# Create audio file
AUDIO_FILE="/tmp/test_audio_complete.mp3"
ffmpeg -f lavfi -i "sine=frequency=1000:duration=2" -f mp3 "$AUDIO_FILE" -y 2>/dev/null

# Submit all sections
echo "3. Submitting all sections..."
for SECTION in $SECTIONS; do
  echo "  Submitting $SECTION..."
  RESPONSE=$(curl -s -X POST "$BASE_URL/v2/structure-practice/$PRACTICE_ID/question/0/section/$SECTION/submit" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$AUDIO_FILE" \
    -F "language=en" \
    -F "time_spent_seconds=30")
  MESSAGE=$(echo "$RESPONSE" | jq -r '.message // .detail')
  echo "    $MESSAGE"
  sleep 0.5
done
echo "✓ All sections submitted"
echo ""

# Analyze
echo "4. Analyzing..."
echo ""
ANALYSIS=$(curl -s -X POST "$BASE_URL/v2/structure-practice/$PRACTICE_ID/question/0/analyze" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "$ANALYSIS" | jq '.'
echo ""

# Summary
COMPLETION=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.completionPercentage // 0')
SECTIONS_DONE=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.sectionsComplete // 0')
TOTAL=$(echo "$ANALYSIS" | jq -r '.frameworkProgress.totalSections // 0')

echo "=========================================="
echo "✅ Test Complete"
echo "=========================================="
echo "Completion: $COMPLETION%"
echo "Sections: $SECTIONS_DONE/$TOTAL"
echo ""

rm -f "$AUDIO_FILE"
