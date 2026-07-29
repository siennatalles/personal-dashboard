from datetime import datetime, timedelta, timezone

from app.briefing import _rule_based_briefing
from app.config import Settings
from app.models import Assignment, CalendarEvent, DashboardResult, EmailItem, Source


def test_empty_dashboard_says_nothing_urgent():
    result = DashboardResult()
    text = _rule_based_briefing(result)
    assert "clear" in text.lower()


def test_mentions_counts_for_each_category():
    now = datetime.now(timezone.utc)
    result = DashboardResult(
        events=[CalendarEvent(id="1", source=Source.APPLE_CALENDAR, title="Meeting", start=now)],
        emails=[EmailItem(id="1", source=Source.GMAIL, subject="Fix now", sender="a@a.com",
                           received_at=now, priority="urgent", needs_reply=True)],
        assignments=[Assignment(id="1", course_name="CS", title="HW1",
                                 due_at=now - timedelta(days=1), submitted=False)],
    )
    text = _rule_based_briefing(result)
    assert "event" in text.lower()
    assert "urgent" in text.lower()
    assert "overdue" in text.lower()


def test_ai_briefing_falls_back_without_api_key():
    from app.briefing import build_briefing
    settings = Settings(demo_mode=True, anthropic_api_key="")
    result = DashboardResult()
    text = build_briefing(result, settings)
    assert isinstance(text, str) and len(text) > 0
