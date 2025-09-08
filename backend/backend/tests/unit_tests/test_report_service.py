import pytest

from src.services.report import FinalReportService
from types import SimpleNamespace


class DummyQA(SimpleNamespace):
    pass


@pytest.mark.asyncio
async def test_generate_for_interview_basic_averages():
    svc = FinalReportService(db=None)  # db not used in aggregation

    qa1 = DummyQA(
        id=1,
        question_text="Q1",
        analysis_json={
            "domain": {"domain_score": 80, "strengths": ["A"], "improvements": ["X"], "knowledge_areas": ["T1", "T2"]},
            "communication": {"communication_score": 60, "clarity_score": 50, "vocabulary_score": 70, "grammar_score": 80, "structure_score": 60, "recommendations": ["R1"]},
            "pace": {"pace_score": 90, "recommendations": ["PR"]},
            "pause": {"pause_score": 70},
        },
    )
    qa2 = DummyQA(
        id=2,
        question_text="Q2",
        analysis_json={
            "domain": {"domain_score": 100, "strengths": ["B"], "improvements": ["Y"], "knowledge_areas": ["T2", "T3"]},
            "communication": {"communication_score": 80, "clarity_score": 70, "vocabulary_score": 80, "grammar_score": 90, "structure_score": 70, "recommendations": ["R2"]},
            "pace": {"pace_score": 70},
            "pause": {"pause_score": 90},
        },
    )

    result = await svc.generate_for_interview(123, [qa1, qa2])

    assert result["interview_id"] == 123
    knowledge = result["knowledge_competence"]
    speech = result["speech_structure_fluency"]

    assert pytest.approx(knowledge["average_domain_score"], 0.001) == 90.0
    assert knowledge["coverage_topics"] == ["T1", "T2", "T3"]

    assert pytest.approx(speech["average_communication_score"], 0.001) == 70.0
    assert pytest.approx(speech["average_pace_score"], 0.001) == 80.0
    assert pytest.approx(speech["average_pause_score"], 0.001) == 80.0

    # Overall is the average of available section scores: 90, 70, 80, 80 = 80
    assert pytest.approx(result["overall_score"], 0.001) == 80.0

    # Recommendations merged and deduped
    assert result["summary"]["per_question"][0]["strengths"]
    assert result["summary"]["per_question"][0]["improvements"]


@pytest.mark.asyncio
async def test_generate_ignores_nan_and_handles_missing_fields():
    svc = FinalReportService(db=None)

    qa = DummyQA(
        id=1,
        question_text=None,
        analysis_json={
            "domain": {"domain_score": float("nan"), "strengths": ["Strong A"], "knowledge_areas": ["Topic"]},
            "communication": {"communication_score": None, "clarity_score": "NaN", "recommendations": ["Be concise", "Be concise"]},
            "pace": {"pace_score": 75, "pace_recommendations": ["Slow down"]},
            "pause": {"pause_score": None, "pause_recommendations": ["Fewer fillers"]},
        },
    )

    res = await svc.generate_for_interview(1, [qa])
    # domain_score NaN -> ignored => average_domain_score should be None
    assert res["knowledge_competence"]["average_domain_score"] is None
    # communication None -> ignored
    assert res["speech_structure_fluency"]["average_communication_score"] is None
    # pace collected
    assert res["speech_structure_fluency"]["average_pace_score"] == 75
    # recommendations deduped and combined
    recs = res["speech_structure_fluency"]["recommendations"]
    assert "Be concise" in recs and recs.count("Be concise") == 1
    assert "Slow down" in recs and "Fewer fillers" in recs
