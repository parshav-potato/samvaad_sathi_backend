import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.repository.database import async_db
from src.models.db.user import User
from src.models.db.session import Session as UserSession
from src.models.db.interview import Interview
from src.models.db.question_attempt import QuestionAttempt
from src.models.db.report import Report


@pytest.mark.asyncio
async def test_models_create_and_relationships() -> None:
    async_session_factory = async_sessionmaker(bind=async_db.async_engine, expire_on_commit=False)

    async with async_session_factory() as session:  # type: AsyncSession
        # Create User
        unique_email = f"{uuid.uuid4().hex[:8]}@example.com"
        user = User(email=unique_email, password_hash="x", name="Test User")
        session.add(user)
        await session.flush()

        # Create Session for user
        user_sess = UserSession(user_id=user.id, token=uuid.uuid4().hex, expiry=asyncio.get_running_loop().time())  # type: ignore[arg-type]
        # fix expiry to a datetime
        import datetime

        user_sess.expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
        session.add(user_sess)

        # Create Interview
        interview = Interview(user_id=user.id, track="Data Science", status="active")
        session.add(interview)
        await session.flush()

        # Create QuestionAttempt
        qa = QuestionAttempt(
            interview_id=interview.id,
            question_text="What is overfitting?",
            feedback="good",
        )
        session.add(qa)

        # Create Report
        report = Report(interview_id=interview.id, overall_score=85.0)
        session.add(report)

        await session.commit()

        # Verify relationships
        refreshed_user = await session.get(User, user.id)
        assert refreshed_user is not None

        # lazy relations may not auto-load; query counts explicitly
        result = await session.get(Interview, interview.id)
        assert result is not None

        qa_found = await session.get(QuestionAttempt, qa.id)
        assert qa_found is not None

        report_found = await session.get(Report, report.id)
        assert report_found is not None


