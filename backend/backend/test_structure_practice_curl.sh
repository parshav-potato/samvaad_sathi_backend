#!/bin/bash

# Test script for structure practice API
# Make sure the server is running on localhost:8000

BASE_URL="http://localhost:8000/api"

echo "=========================================="
echo "Structure Practice API Test"
echo "=========================================="
echo ""

# Step 1: Register a test user
echo "1. Registering test user..."
REGISTER_RESPONSE=$(curl -s -X POST "${BASE_URL}/users" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "structure_test_'$(date +%s)'@example.com",
    "password": "Test@1234",
    "name": "Structure Test User"
  }')

echo "$REGISTER_RESPONSE" | jq '.'
TOKEN=$(echo "$REGISTER_RESPONSE" | jq -r '.authorizedUser.token // empty')

if [ -z "$TOKEN" ]; then
  echo "❌ Failed to register user"
  exit 1
fi

echo "✓ User registered, token obtained"
echo ""

# Step 2: Create structure practice session WITHOUT interview_id (should create new interview)
echo "2. Creating structure practice session (no interview_id, with track and difficulty)..."
PRACTICE_RESPONSE=$(curl -s -X POST "${BASE_URL}/v2/structure-practice/session" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track": "JavaScript Developer",
    "difficulty": "easy"
  }')

echo "$PRACTICE_RESPONSE" | jq '.'
PRACTICE_ID=$(echo "$PRACTICE_RESPONSE" | jq -r '.practiceId // empty')

if [ -z "$PRACTICE_ID" ]; then
  echo "❌ Failed to create practice session"
  exit 1
fi

echo "✓ Practice session created: $PRACTICE_ID"
echo ""

# Step 3: Validate response fields
echo "3. Validating response fields..."
INTERVIEW_ID=$(echo "$PRACTICE_RESPONSE" | jq -r '.interviewId // empty')
TRACK=$(echo "$PRACTICE_RESPONSE" | jq -r '.track // empty')
QUESTION_COUNT=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions | length')

echo "  Interview ID: $INTERVIEW_ID"
echo "  Track: $TRACK"
echo "  Question Count: $QUESTION_COUNT"

if [ "$INTERVIEW_ID" == "null" ] || [ -z "$INTERVIEW_ID" ]; then
  echo "❌ Interview ID should not be null"
  exit 1
fi

if [ "$QUESTION_COUNT" -lt 1 ]; then
  echo "❌ Should have at least 1 question"
  exit 1
fi

# Check if questions have question_id
FIRST_QUESTION_ID=$(echo "$PRACTICE_RESPONSE" | jq -r '.questions[0].question_id // empty')
if [ "$FIRST_QUESTION_ID" == "null" ] || [ -z "$FIRST_QUESTION_ID" ]; then
  echo "❌ First question should have question_id (not null)"
  exit 1
fi

echo "✓ All fields populated correctly"
echo ""

echo "=========================================="
echo "✅ ALL TESTS PASSED"
echo "=========================================="
