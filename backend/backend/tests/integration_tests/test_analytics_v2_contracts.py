from src.main import initialize_backend_application


def test_analytics_v2_paths_registered() -> None:
    app = initialize_backend_application()
    schema = app.openapi()
    paths = schema.get("paths", {})

    expected_paths = [
        "/api/v2/analytics/dashboard/overview",
        "/api/v2/analytics/dashboard/interviews-per-day",
        "/api/v2/analytics/dashboard/active-users-trend",
        "/api/v2/analytics/dashboard/top-roles",
        "/api/v2/analytics/dashboard/top-colleges",
        "/api/v2/analytics/dashboard/score-distribution",
        "/api/v2/analytics/dashboard/recent-interviews",
        "/api/v2/analytics/dashboard/recent-students",
        "/api/v2/analytics/dashboard/attention-required",
        "/api/v2/analytics/students/summary",
        "/api/v2/analytics/students",
        "/api/v2/analytics/students/search",
        "/api/v2/analytics/students/filters/colleges",
        "/api/v2/analytics/students/{student_id}/profile",
        "/api/v2/analytics/students/{student_id}/summary",
        "/api/v2/analytics/students/{student_id}/score-history",
        "/api/v2/analytics/students/{student_id}/speech-vs-knowledge-history",
        "/api/v2/analytics/students/{student_id}/skill-averages",
        "/api/v2/analytics/students/{student_id}/practice-completion",
        "/api/v2/analytics/students/{student_id}/interviews",
        "/api/v2/analytics/students/{student_id}/latest-feedback",
        "/api/v2/analytics/colleges/summary",
        "/api/v2/analytics/colleges",
        "/api/v2/analytics/colleges/{college_name}/summary",
        "/api/v2/analytics/colleges/{college_name}/student-growth",
        "/api/v2/analytics/colleges/{college_name}/score-trend",
        "/api/v2/analytics/colleges/{college_name}/practice-metrics",
        "/api/v2/analytics/colleges/{college_name}/weak-skills",
        "/api/v2/analytics/colleges/{college_name}/students",
        "/api/v2/analytics/rankings/summary",
        "/api/v2/analytics/rankings/top-performers",
        "/api/v2/analytics/rankings/struggling",
        "/api/v2/analytics/rankings/most-improved",
        "/api/v2/analytics/interviews/summary",
        "/api/v2/analytics/interviews",
        "/api/v2/analytics/interviews/{interview_id}/summary",
        "/api/v2/analytics/interviews/{interview_id}/question-scores",
        "/api/v2/analytics/interviews/{interview_id}/speech-metrics-timeline",
        "/api/v2/analytics/interviews/{interview_id}/question-type-breakdown",
        "/api/v2/analytics/roles/summary",
        "/api/v2/analytics/roles/performance",
        "/api/v2/analytics/roles/weak-skills",
        "/api/v2/analytics/roles/{role_id}",
        "/api/v2/analytics/difficulty/metrics",
        "/api/v2/analytics/questions/analytics",
        "/api/v2/analytics/dropoffs/funnel",
        "/api/v2/analytics/search",
        "/api/v2/analytics/insights/predictive-alerts",
        "/api/v2/analytics/insights/benchmarking",
        "/api/v2/analytics/insights/forecasting",
    ]

    missing = [path for path in expected_paths if path not in paths]
    assert not missing, f"Missing analytics v2 paths: {missing}"


def test_analytics_v2_get_routes_require_bearer_security() -> None:
    app = initialize_backend_application()
    schema = app.openapi()
    paths = schema.get("paths", {})

    analytics_v2_paths = {
        path: operations
        for path, operations in paths.items()
        if path.startswith("/api/v2/analytics/")
    }

    assert analytics_v2_paths, "No v2 analytics paths found in OpenAPI"

    missing_security: list[str] = []
    for path, operations in analytics_v2_paths.items():
        get_op = operations.get("get")
        if not get_op:
            continue
        security = get_op.get("security", [])
        has_bearer = any("HTTPBearer" in requirement for requirement in security)
        if not has_bearer:
            missing_security.append(path)

    assert not missing_security, f"Analytics v2 GET routes missing bearer security: {missing_security}"
