import pytest
from types import SimpleNamespace
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession as SQLAlchemyAsyncSession

from src.models.db.question_attempt import QuestionAttempt
from src.services import summary_report as summary_report_module
from src.services.summary_report import SummaryReportService


class DummyQA(SimpleNamespace):
    pass


@pytest.mark.asyncio
async def test_per_question_analysis_deduplicated(monkeypatch):
    service = SummaryReportService(db=cast(SQLAlchemyAsyncSession, None))

    qa = DummyQA(
        id=194,
        question_text="Actual question text",
        analysis_json={
            "domain": {
                "criteria": {},
                "strengths": ["Solid reasoning"],
                "improvements": ["Stay on topic"],
                "knowledge_areas": ["async"],
            },
            "communication": {
                "criteria": {},
                "recommendations": ["Be concise"],
            },
            "pace": {},
            "pause": {},
        },
    )

    async def fake_synthesize_summary_sections(**kwargs):
        return (
            {
                "perQuestion": [
                    {
                        "questionAttemptId": 194,
                        "knowledgeScorePct": 0,
                        "speechScorePct": 66.5,
                        "keyTakeaways": ["Stay on topic"],
                    }
                ],
                "perQuestionAnalysis": [
                    {
                        "questionAttemptId": 194,
                        "questionText": "Incorrect question text",
                        "keyTakeaways": ["Stay on topic", "Stay on topic"],
                        "speechScorePct": 66.5,
                    },
                    {
                        "questionAttemptId": 194,
                        "questionText": "Another wrong text",
                        "keyTakeaways": [
                            "Stay on topic",
                            "Focus on async control flow",
                        ],
                    },
                ],
            },
            None,
            123,
            "mock-model",
        )

    monkeypatch.setattr(
        summary_report_module,
        "synthesize_summary_sections",
        fake_synthesize_summary_sections,
    )

    result = await service.generate_for_interview(
        interview_id=35,
        question_attempts=[cast(QuestionAttempt, qa)],
        track="javascript developer",
        resume_used=True,
    )

    assert "perQuestion" not in result
    per_question_analysis = result["perQuestionAnalysis"]
    assert len(per_question_analysis) == 1
    analysis_entry = per_question_analysis[0]
    assert analysis_entry["questionAttemptId"] == 194
    # The canonical question text from the attempt should be preserved
    assert analysis_entry["questionText"] == "Actual question text"
    # Key takeaways are deduped and capped
    assert analysis_entry["keyTakeaways"] == [
        "Stay on topic",
        "Focus on async control flow",
    ]
    # Speech score percentile maintained when provided by LLM
    assert analysis_entry["speechScorePct"] == 66.5