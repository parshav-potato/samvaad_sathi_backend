from __future__ import annotations

import datetime
from typing import Any

import pydantic

from src.models.schemas.base import BaseSchemaModel


class AnalyticsQueryFilters(BaseSchemaModel):
    start_date: datetime.date | None = None
    end_date: datetime.date | None = None
    role: str | None = None
    difficulty: str | None = None
    college: str | None = None


class StudentAnalyticsResponse(BaseSchemaModel):
    user_id: int
    filters: AnalyticsQueryFilters
    metrics: dict[str, Any]


class InterviewAnalyticsResponse(BaseSchemaModel):
    interview_id: int
    metrics: dict[str, Any]


class SegmentAnalyticsResponse(BaseSchemaModel):
    segment: str
    filters: AnalyticsQueryFilters
    items: list[dict[str, Any]]


class SystemAnalyticsResponse(BaseSchemaModel):
    filters: AnalyticsQueryFilters
    metrics: dict[str, Any]


class ScoringAnalyticsResponse(BaseSchemaModel):
    filters: AnalyticsQueryFilters
    metrics: dict[str, Any]


class AlertsAnalyticsResponse(BaseSchemaModel):
    filters: AnalyticsQueryFilters
    student_alerts: list[dict[str, Any]]
    system_alerts: list[dict[str, Any]]


class AlertsQueryParams(BaseSchemaModel):
    user_id: int | None = pydantic.Field(default=None, gt=0)


class ReportEngagementRequest(BaseSchemaModel):
    interview_id: int | None = pydantic.Field(default=None, gt=0)
    time_spent_seconds: int | None = pydantic.Field(default=None, ge=0)
    recommendation_clicks: int | None = pydantic.Field(default=None, ge=0)
    report_type: str | None = None

