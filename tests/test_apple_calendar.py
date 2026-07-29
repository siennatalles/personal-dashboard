"""Apple Calendar connector: demo fallback + real-mode parsing (CalDAV mocked)."""
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from icalendar import Event as ICalEvent

from app.config import Settings
from app.connectors import apple_calendar
from app.models import Source


def test_demo_fallback_when_not_configured():
    settings = Settings(demo_mode=False, apple_id="", apple_app_password="")
    events, status = apple_calendar.fetch(settings)
    assert status.demo is True
    assert status.ok is True
    assert status.configured is False
    assert len(events) > 0
    assert all(e.source == Source.APPLE_CALENDAR for e in events)


def _fake_vevent(summary, dtstart, dtend=None, location=None, uid="uid-1"):
    ev = ICalEvent()
    ev.add("summary", summary)
    ev.add("dtstart", dtstart)
    if dtend:
        ev.add("dtend", dtend)
    if location:
        ev.add("location", location)
    ev.add("uid", uid)
    return ev


def test_real_fetch_parses_timed_and_allday_events():
    settings = Settings(demo_mode=False, apple_id="me@icloud.com",
                         apple_app_password="app-specific-pw")

    timed_event = _fake_vevent(
        "Standup", datetime(2026, 7, 22, 9, 0), datetime(2026, 7, 22, 9, 15),
        location="Zoom", uid="timed-1",
    )
    allday_event = _fake_vevent("Birthday", date(2026, 7, 25), uid="allday-1")

    fake_result_1 = MagicMock()
    fake_result_1.icalendar_instance.walk.return_value = [timed_event]
    fake_result_2 = MagicMock()
    fake_result_2.icalendar_instance.walk.return_value = [allday_event]

    fake_calendar = MagicMock()
    fake_calendar.name = "Personal"
    fake_calendar.date_search.return_value = [fake_result_1, fake_result_2]

    fake_principal = MagicMock()
    fake_principal.calendars.return_value = [fake_calendar]

    fake_client = MagicMock()
    fake_client.principal.return_value = fake_principal

    with patch("caldav.DAVClient", return_value=fake_client) as mock_dav:
        events, status = apple_calendar.fetch(settings)

    mock_dav.assert_called_once()
    _, kwargs = mock_dav.call_args
    assert kwargs["username"] == "me@icloud.com"
    assert kwargs["password"] == "app-specific-pw"

    assert status.ok is True
    assert status.demo is False
    assert len(events) == 2

    timed = next(e for e in events if e.id == "timed-1")
    assert timed.title == "Standup"
    assert timed.all_day is False
    assert timed.location == "Zoom"
    # model normalizes naive datetimes to UTC-aware at the boundary (see
    # test_models.py) — the parser itself hands back naive here, so assert
    # against the aware equivalent.
    assert timed.start == datetime(2026, 7, 22, 9, 0, tzinfo=timezone.utc)

    allday = next(e for e in events if e.id == "allday-1")
    assert allday.all_day is True
    assert allday.start == datetime(2026, 7, 25, 0, 0, tzinfo=timezone.utc)


def test_real_fetch_surfaces_errors_without_crashing():
    settings = Settings(demo_mode=False, apple_id="me@icloud.com",
                         apple_app_password="wrong-password")
    with patch("caldav.DAVClient", side_effect=RuntimeError("401 Unauthorized")):
        events, status = apple_calendar.fetch(settings)

    assert events == []
    assert status.ok is False
    assert "Unauthorized" in status.error
