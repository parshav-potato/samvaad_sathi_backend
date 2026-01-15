# Structure Practice Section-by-Section Analysis - Updated

## Overview

The report generation and analysis functionality has been updated to work with the section-by-section submission model.

## Key Changes

### 1. Analysis Endpoint Updates (`src/api/routes/interviews_v2.py`)

**Endpoint**: `POST /v2/structure-practice/{practice_id}/question/{question_index}/analyze`

**Changes**:
- Now retrieves ALL section answers for a question using `list_by_practice_and_question()`
- Combines section answers in framework order: `[Context]\n<answer>\n\n[Theory]\n<answer>...`
- Passes submitted sections data to analysis service
- Uses actual recorded time per section instead of estimates
- Stores analysis on the most recent section answer

**Before**:
```python
# Get single answer
answer = await answer_repo.get_answer(practice_id, question_index)
analysis = await analyze_structure_answer(answer.answer_text)
```

**After**:
```python
# Get all section answers
section_answers = await answer_repo.list_by_practice_and_question(practice_id, question_index)

# Combine sections
sections_data = {ans.section_name: {
    "answer_text": ans.answer_text,
    "time_spent_seconds": ans.time_spent_seconds,
    "submitted": True
} for ans in section_answers}

combined_answer = "\n\n".join([
    f"[{section}]\n{sections_data[section]['answer_text']}"
    for section in expected_sections if section in sections_data
])

# Analyze with section context
analysis = await analyze_structure_answer(
    answer_text=combined_answer,
    framework=framework,
    submitted_sections=sections_data,
    expected_sections=expected_sections
)
```

### 2. Analysis Service Updates (`src/services/structure_analysis.py`)

**Function**: `async def analyze_structure_answer(...)`

**New Parameters**:
- `framework: str = None` - Framework type (STAR, C-T-E-T-D, GCDIO)
- `submitted_sections: dict = None` - Map of section_name → {answer_text, time_spent_seconds, submitted}
- `expected_sections: list[str] = None` - List of expected section names

**Enhanced LLM Prompt**:
```
The user submitted answers section-by-section. Each section is marked with [Section Name].

Sections submitted by user:
- Context: SUBMITTED (30s)
- Theory: SUBMITTED (40s)
- Example: NOT SUBMITTED
- Trade-offs: SUBMITTED (35s)
- Decision: NOT SUBMITTED

Analyze each SUBMITTED section for quality (good/partial).
Mark non-submitted sections as 'missing' with quality='missing'.
Use actual recorded time for submitted sections.

Calculate completion percentage:
- 50% weight for sections submitted
- 50% weight for quality of submitted sections
```

**Analysis Logic**:
1. Identifies which sections were submitted vs. missing
2. Assesses quality of each SUBMITTED section (good/partial/missing)
3. Uses ACTUAL time spent from user recordings
4. Calculates completion: `(sections_submitted/total * 50) + (quality_score/100 * 50)`
5. Provides specific insight on what was done well and what needs improvement

### 3. Response Structure

**StructurePracticeAnalysisResponse**:
```json
{
  "answerId": 6,
  "practiceId": 13,
  "questionIndex": 0,
  "frameworkProgress": {
    "frameworkName": "C-T-E-T-D",
    "sections": [
      {
        "name": "Context",
        "status": "complete",      // "complete" | "partial" | "missing"
        "answerRecorded": true,
        "timeSpentSeconds": 30     // ACTUAL recorded time
      },
      {
        "name": "Theory",
        "status": "complete",
        "answerRecorded": true,
        "timeSpentSeconds": 40
      },
      {
        "name": "Example",
        "status": "missing",        // Not submitted
        "answerRecorded": false,
        "timeSpentSeconds": 0
      },
      {
        "name": "Trade-offs",
        "status": "partial",        // Submitted but underdeveloped
        "answerRecorded": true,
        "timeSpentSeconds": 35
      },
      {
        "name": "Decision",
        "status": "missing",
        "answerRecorded": false,
        "timeSpentSeconds": 0
      }
    ],
    "completionPercentage": 65,   // Based on sections + quality
    "sectionsComplete": 3,          // Actually submitted
    "totalSections": 5,
    "progressMessage": "Good progress! You've covered Context and Theory well. Focus on completing the remaining sections."
  },
  "timePerSection": [
    {"sectionName": "Context", "seconds": 30},
    {"sectionName": "Theory", "seconds": 40},
    {"sectionName": "Example", "seconds": 0},
    {"sectionName": "Trade-offs", "seconds": 35},
    {"sectionName": "Decision", "seconds": 0}
  ],
  "keyInsight": "Strong conceptual foundation with Context and Theory. Example section is missing which would strengthen your answer. Trade-offs could be more detailed with specific pros/cons. Complete the Decision section to conclude your response.",
  "analyzedAt": "2026-01-15T18:45:30.123456Z",
  "llmModel": "gpt-4o-chat-latest",
  "llmLatencyMs": 4200
}
```

## Usage Flow

### Complete Workflow

1. **Create Session**
   ```
   POST /v2/structure-practice/session
   → Returns: framework, sections, current_section, current_hint
   ```

2. **Submit Each Section** (repeat for each section)
   ```
   POST /v2/structure-practice/{id}/question/{index}/section/{section_name}/submit
   → Returns: nextSection, nextSectionHint, sectionsComplete, isComplete
   ```

3. **Analyze Complete Answer** (when isComplete=true or user requests)
   ```
   POST /v2/structure-practice/{id}/question/{index}/analyze
   → Returns: Complete analysis with framework progress, time breakdown, insights
   ```

### Analysis Triggers

**When to call analyze**:
- ✅ After all sections are submitted (`isComplete=true`)
- ✅ User manually requests analysis (even with incomplete sections)
- ✅ At any point to get progress feedback

**Partial Completion**:
- Analysis works even if not all sections are submitted
- Missing sections are marked with `status="missing"` and `answerRecorded=false`
- Completion percentage reflects both quantity and quality
- Key insight highlights what's missing and what needs improvement

## Benefits

1. **Accurate Time Tracking**: Uses actual user recording time, not estimates
2. **Section-Level Feedback**: Shows exactly which sections are strong/weak/missing
3. **Progressive Guidance**: Can analyze at any stage for feedback
4. **Framework-Aware**: Understands STAR, C-T-E-T-D, and GCDIO patterns
5. **Quality Assessment**: Distinguishes between "submitted" and "well-developed"

## Testing

The analysis functionality has been updated and is ready for testing once section submissions are working reliably. The key improvement is that it now:

1. Gathers all section answers from the database
2. Combines them in the correct order with section labels
3. Passes the framework context and submission details to the LLM
4. Returns detailed feedback on each section's presence and quality
5. Uses actual time spent from user recordings

## Database State

Current sections in database (as of last check):
- Practice 13: 1 section (Context) - can be used for testing partial analysis
- Practice 10: 1 section (Situation) 
- Practice 9: 1 section (Situation)

To test complete analysis, all sections for a question need to be submitted first.
