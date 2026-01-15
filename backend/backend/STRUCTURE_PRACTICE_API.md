# Structure Practice API - Section-by-Section Flow

## Overview
Structure practice now uses a section-by-section approach where you record audio for each part of the framework (C-T-E-T-D, STAR, or GCDIO) separately, receiving progressive hints along the way.

## API Flow

### 1. Create Structure Practice Session

**Endpoint:** `POST /api/v2/structure-practice/session`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v2/structure-practice/session" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "track": "JavaScript Developer",
    "difficulty": "easy"
  }'
```

**Response:**
```json
{
  "practiceId": 6,
  "interviewId": 313,
  "track": "JavaScript Developer",
  "questions": [
    {
      "text": "Explain the concept of closures in JavaScript and provide a practical use case.",
      "index": 0,
      "question_id": 1231,
      "structure_hint": "Use C-T-E-T-D: explain the context of scope in JS, define closure theory, show a practical example, discuss trade-offs like memory considerations, and conclude with when to use closures.",
      "framework": "C-T-E-T-D",
      "sections": ["Context", "Theory", "Example", "Trade-offs", "Decision"],
      "current_section": "Context",
      "current_hint": "Start with Context: Set the stage. Explain the background, scenario, or environment where this concept applies."
    }
  ],
  "status": "active",
  "createdAt": "2026-01-15T18:00:00Z"
}
```

---

### 2. Submit Section Audio (Repeat for Each Section)

**Endpoint:** `POST /api/v2/structure-practice/{practice_id}/question/{question_index}/section/{section_name}/submit`

**Example - Submit Context Section:**
```bash
curl -X POST "http://localhost:8000/api/v2/structure-practice/6/question/0/section/Context/submit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/context_answer.mp3" \
  -F "language=en" \
  -F "time_spent_seconds=30"
```

**Response:**
```json
{
  "answerId": 1,
  "practiceId": 6,
  "questionIndex": 0,
  "sectionName": "Context",
  "sectionsComplete": 1,
  "totalSections": 5,
  "nextSection": "Theory",
  "nextSectionHint": "Great start! Now move to Theory. Define the core concept. Explain how it works, key principles, or the underlying mechanism.",
  "isComplete": false,
  "message": "Section 'Context' recorded successfully (whisper-1, 5432ms). Continue to Theory."
}
```

**Example - Submit Theory Section:**
```bash
curl -X POST "http://localhost:8000/api/v2/structure-practice/6/question/0/section/Theory/submit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/theory_answer.mp3" \
  -F "language=en" \
  -F "time_spent_seconds=45"
```

**Response:**
```json
{
  "answerId": 2,
  "practiceId": 6,
  "questionIndex": 0,
  "sectionName": "Theory",
  "sectionsComplete": 2,
  "totalSections": 5,
  "nextSection": "Example",
  "nextSectionHint": "Good progress! Next is Example. Provide a concrete example. Show working code, a real scenario, or a practical demonstration.",
  "isComplete": false,
  "message": "Section 'Theory' recorded successfully (whisper-1, 4821ms). Continue to Example."
}
```

**Continue for remaining sections:** Example → Trade-offs → Decision

**Final Section Response (Decision):**
```json
{
  "answerId": 5,
  "practiceId": 6,
  "questionIndex": 0,
  "sectionName": "Decision",
  "sectionsComplete": 5,
  "totalSections": 5,
  "nextSection": null,
  "nextSectionHint": null,
  "isComplete": true,
  "message": "Excellent! You've completed all sections of the C-T-E-T-D framework. Your answer will now be analyzed."
}
```

---

### 3. Analyze Complete Answer

**Endpoint:** `POST /api/v2/structure-practice/{practice_id}/question/{question_index}/analyze`

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v2/structure-practice/6/question/0/analyze" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "answerId": 5,
  "practiceId": 6,
  "questionIndex": 0,
  "frameworkProgress": {
    "frameworkName": "C-T-E-T-D",
    "sections": [
      {
        "name": "Context",
        "status": "complete",
        "answerRecorded": true,
        "timeSpentSeconds": 30
      },
      {
        "name": "Theory",
        "status": "complete",
        "answerRecorded": true,
        "timeSpentSeconds": 45
      },
      {
        "name": "Example",
        "status": "complete",
        "answerRecorded": true,
        "timeSpentSeconds": 60
      },
      {
        "name": "Trade-offs",
        "status": "partial",
        "answerRecorded": true,
        "timeSpentSeconds": 25
      },
      {
        "name": "Decision",
        "status": "complete",
        "answerRecorded": true,
        "timeSpentSeconds": 20
      }
    ],
    "completionPercentage": 90,
    "sectionsComplete": 5,
    "totalSections": 5,
    "progressMessage": "Excellent work! You covered all sections. Trade-offs could be expanded with more depth."
  },
  "timePerSection": [
    {"sectionName": "Context", "seconds": 30},
    {"sectionName": "Theory", "seconds": 45},
    {"sectionName": "Example", "seconds": 60},
    {"sectionName": "Trade-offs", "seconds": 25},
    {"sectionName": "Decision", "seconds": 20}
  ],
  "keyInsight": "Strong technical explanation with good examples. Consider elaborating more on memory implications and performance trade-offs of closures in production code.",
  "analyzedAt": "2026-01-15T18:15:00Z",
  "llmModel": "gpt-5-chat-latest",
  "llmLatencyMs": 4200
}
```

---

## Frameworks

### C-T-E-T-D (Technical Questions)
Sections: **Context → Theory → Example → Trade-offs → Decision**

### STAR (Behavioral Questions)
Sections: **Situation → Task → Action → Result**

### GCDIO (System Design / Architecture)
Sections: **Goal → Constraints → Decision → Implementation → Outcome**

---

## Error Responses

### Invalid Section Name
```json
{
  "detail": "Invalid section_name 'InvalidSection' for framework C-T-E-T-D. Valid sections: ['Context', 'Theory', 'Example', 'Trade-offs', 'Decision']"
}
```

### Question Index Out of Range
```json
{
  "detail": "question_index 10 out of range for this practice session"
}
```

---

## Notes

1. **Progressive Hints**: Each submission returns a hint for the next section
2. **Framework Detection**: Automatically detects which framework based on question type
3. **Section Order**: Submit sections in order (Context → Theory → Example → Trade-offs → Decision)
4. **Time Tracking**: Track time per section for detailed analysis
5. **Analysis**: Call analyze endpoint only after all sections are submitted
