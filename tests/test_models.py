"""Regression tests for the naive/aware datetime crash: real Apple Calendar
data (timezone-aware, from CalDAV) mixed with naive demo data used to raise
`TypeError: can't compare offset-naive and offset-aware datetimes` the
moment both landed in one sorted() call. Every datetime field must come out
of the model tagged UTC-aware regardless of what went in."""
from datetime import datetime, timezone

from app.models import Assignment, CalendarEvent, EmailItem, Source


def test_naive_datetime_becomes_utc_aware():
    e = CalendarEvent(id="1", source=Source.APPLE_CALENDAR, title="x",
                       start=datetime(2026, 7, 22, 9, 0))  # naive
    assert e.start.tzinfo is not None
    assert e.start.utcoffset().total_seconds() == 0


def test_already_aware_datetime_is_left_alone():
    aware = datetime(2026, 7, 22, 9, 0, tzinfo=timezone.utc)
    e = CalendarEvent(id="1", source=Source.APPLE_CALENDAR, title="x", start=aware)
    assert e.start == aware


def test_mixed_naive_and_aware_events_sort_without_crashing():
    naive_event = CalendarEvent(id="a", source=Source.APPLE_CALENDAR, title="Demo",
                                 start=datetime(2026, 7, 22, 15, 0))  # naive, like demo data
    aware_event = CalendarEvent(id="b", source=Source.APPLE_CALENDAR, title="Apple",
                                 start=datetime(2026, 7, 22, 9, 0, tzinfo=timezone.utc))  # aware, like real CalDAV

    result = sorted([naive_event, aware_event], key=lambda e: e.start)  # must not raise
    assert [e.id for e in result] == ["b", "a"]


def test_multiple_undated_assignments_sort_without_crashing():
    from app.orchestrator import _FAR_FUTURE

    a1 = Assignment(id="1", course_name="CS", title="No due date A", due_at=None)
    a2 = Assignment(id="2", course_name="CS", title="No due date B", due_at=None)
    dated = Assignment(id="3", course_name="CS", title="Has due date",
                        due_at=datetime(2026, 7, 22, tzinfo=timezone.utc))

    result = sorted([a1, a2, dated], key=lambda a: a.due_at or _FAR_FUTURE)  # must not raise
    assert result[0].id == "3"  # dated one sorts first


def test_email_received_at_normalized():
    e = EmailItem(id="1", source=Source.GMAIL, subject="s", sender="a@a.com",
                   received_at=datetime(2026, 7, 22, 9, 0))
    assert e.received_at.tzinfo is not None
