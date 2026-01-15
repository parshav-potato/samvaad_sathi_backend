#!/bin/bash

# Test script for section-by-section structure practice
BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "Structure Practice Section-by-Section Test"
echo "=========================================="
echo ""

# Step 1: Register test user
echo "1. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "${BASE_URL}/users" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "structure_section_test_'$(date +%s)'@example.com",
    "password": "Test@1234",
    "name": "Structure Section Test"
  }')

TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.authorizedUser.token // empty')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to register user"
  exit 1
fi
echo "✓ User registered"
echo ""

# Step 2: Create practice session
echo "2. Creating structure practice session..."
PRACTICE_RESPONSE=$(curl -s -X POST "${BASE_URL}/v2/structure-practice/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track": "JavaScript Developer",
    "difficulty": "easy"
  }')

echo "$PRACTICE_RESPONSE" | jq '.'

PRACTICE_ID=$(echo "$PRACTICE_RESPONSE" | jq -r '.practiceId // empty')
FRAMEWORK=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].framework // empty')
FIRST_SECTION=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].current_section // empty')
CURRENT_HINT=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].current_hint // empty')
SECTIONS=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].sections // empty')

echo ""
echo "Practice ID: $PRACTICE_ID"
echo "Framework: $FRAMEWORK"
echo "First Section: $FIRST_SECTION"
echo "Sections: $SECTIONS"
echo ""

if [ -z "$PRACTICE_ID" ] || [ "$PRACTICE_ID" == "null" ]; then
  echo "❌ Failed to create practice session"
  exit 1
fi

if [ -z "$FRAMEWORK" ] || [ "$FRAMEWORK" == "null" ]; then
  echo "❌ Framework not detected"
  exit 1
fi

if [ -z "$FIRST_SECTION" ] || [ "$FIRST_SECTION" == "null" ]; then
  echo "❌ First section not provided"
  exit 1
fi

echo "✓ Practice session created with framework info"
echo ""

# Step 3: Test section submission (if audio file exists)
AUDIO_FILE="/home/parshav-potato/projects/samvaad_sathi_backend/backend/backend/assets/Speech.mp3"

if [ ! -f "$AUDIO_FILE" ]; then
  echo "⚠ Audio file not found at $AUDIO_FILE"
  echo "Skipping section submission test"
else
  echo "3. Submitting first section ($FIRST_SECTION)..."
  SUBMIT_RESPONSE=$(curl -s -X POST "${BASE_URL}/v2/structure-practice/${PRACTICE_ID}/question/0/section/${FIRST_SECTION}/submit" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@${AUDIO_FILE}" \
    -F "language=en" \
    -F "time_spent_seconds=30")
  
  echo "$SUBMIT_RESPONSE" | jq '.'
  echo ""
  
  NEXT_SECTION=$(echo "$SUBMIT_RESPONSE" | jq -r '.nextSection // empty')
  NEXT_HINT=$(echo "$SUBMIT_RESPONSE" | jq -r '.nextSectionHint // empty')
  SECTIONS_COMPLETE=$(echo "$SUBMIT_RESPONSE" | jq -r '.sectionsComplete // empty')
  IS_COMPLETE=$(echo "$SUBMIT_RESPONSE" | jq -r '.isComplete // empty')
  
  echo "Sections Complete: $SECTIONS_COMPLETE"
  echo "Next Section: $NEXT_SECTION"
  echo "Is Complete: $IS_COMPLETE"
  echo ""
  
  if [ -z "$NEXT_SECTION" ] || [ "$NEXT_SECTION" == "null" ]; then
    echo "❌ Next section not provided"
    exit 1
  fi
  
  if [ -z "$NEXT_HINT" ] || [ "$NEXT_HINT" == "null" ]; then
    echo "❌ Next section hint not provided"
    exit 1
  fi
  
  echo "✓ Section submitted successfully with progressive hint"
  echo ""
  echo "Next hint preview: ${NEXT_HINT:0:100}..."
  echo ""
fi

echo "=========================================="
echo "✅ ALL TESTS PASSED"
echo "=========================================="
