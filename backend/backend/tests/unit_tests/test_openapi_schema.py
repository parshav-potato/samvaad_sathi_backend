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
