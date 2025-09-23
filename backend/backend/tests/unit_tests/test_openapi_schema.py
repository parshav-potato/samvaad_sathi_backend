import pytest
from src.main import initialize_backend_application


def test_openapi_includes_report_and_analysis_paths_without_startup():
    app = initialize_backend_application()
    schema = app.openapi()

    assert "openapi" in schema
    assert "paths" in schema

    paths = schema["paths"]
    assert "/api/final-report" in paths
    assert "/api/final-report/{interview_id}" in paths
    assert "/api/complete-analysis" in paths
    assert "/api/domain-base-analysis" in paths
    assert "/api/communication-based-analysis" in paths

    tags = schema.get("tags", [])
    tag_names = {t.get("name") for t in tags}
    assert {"users", "resume", "interviews", "audio", "analysis", "report"}.issubset(tag_names)


def test_final_report_response_has_example_without_startup():
    app = initialize_backend_application()
    schema = app.openapi()

    components = schema.get("components", {})
    schemas = components.get("schemas", {})

    fr_schema = schemas.get("FinalReportResponse")
    assert fr_schema is not None
    properties = fr_schema.get("properties", {})
    assert "interviewId" in properties
    assert "summary" in properties
    assert "knowledgeCompetence" in properties
    assert "speechStructureFluency" in properties
    assert "overallScore" in properties


def test_interview_schemas_include_question_ids():
    app = initialize_backend_application()
    schema = app.openapi()

    components = schema.get("components", {})
    schemas = components.get("schemas", {})

    # Check QuestionItem schema includes category field
    qi_schema = schemas.get("QuestionItem")
    assert qi_schema is not None
    props = qi_schema.get("properties", {})
    assert "category" in props
    assert "text" in props
    assert "topic" in props
    assert "difficulty" in props

    # Check GeneratedQuestionsInResponse includes question_ids
    gq_schema = schemas.get("GeneratedQuestionsInResponse")
    assert gq_schema is not None
    gq_props = gq_schema.get("properties", {})
    assert "question_ids" in gq_props
    assert "questions" in gq_props
    assert "cached" in gq_props