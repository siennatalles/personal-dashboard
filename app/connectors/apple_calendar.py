"""Apple Calendar via CalDAV (caldav.icloud.com).

Auth: Apple ID email + an app-specific password (Settings > [name] >
Sign-In & Security > App-Specific Passwords). Requires 2FA on the account.
This is the only third-party-accessible protocol Apple exposes for Calendar
— there's no OAuth/REST API. See README.md for setup steps.
"""
from __future__ import annotations

from typing import List, Tuple

from ..config import Settings
from ..demo_data import demo_apple_events
from ..models import CalendarEvent, Source, SourceStatus
from .common import default_window, is_all_day, simulate_latency, status_error, status_ok, timed, to_datetime

ICLOUD_CALDAV_URL = "https://caldav.icloud.com/"


def fetch(settings: Settings) -> Tuple[List[CalendarEvent], SourceStatus]:
    if settings.demo_mode or not settings.apple_configured:
        with timed() as t:
            simulate_latency()
            events = demo_apple_events()
        return events, status_ok(Source.APPLE_CALENDAR, len(events), t["ms"],
                                  demo=True, configured=settings.apple_configured)

    with timed() as t:
        try:
            events = _fetch_real(settings)
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            return [], status_error(Source.APPLE_CALENDAR, t["ms"], True, str(exc))
    return events, status_ok(Source.APPLE_CALENDAR, len(events), t["ms"], demo=False, configured=True)


def _fetch_real(settings: Settings) -> List[CalendarEvent]:
    import caldav  # imported lazily so demo mode never requires the package

    client = caldav.DAVClient(
        url=ICLOUD_CALDAV_URL,
        username=settings.apple_id,
        password=settings.apple_app_password,
    )
    principal = client.principal()
    start, end = default_window()

    events: List[CalendarEvent] = []
    for calendar in principal.calendars():
        try:
            results = calendar.date_search(start=start, end=end, expand=True)
        except Exception:
            continue  # some calendars (e.g. subscribed read-only ones) may reject search
        cal_name = getattr(calendar, "name", None) or "Calendar"
        for result in results:
            for component in result.icalendar_instance.walk("VEVENT"):
                uid = str(component.get("UID", f"apple-{len(events)}"))
                summary = str(component.get("SUMMARY", "(untitled event)"))
                dtstart_raw = component.get("DTSTART")
                dtend_raw = component.get("DTEND")
                location = component.get("LOCATION")
                start_val = dtstart_raw.dt if dtstart_raw else None
                events.append(CalendarEvent(
                    id=uid,
                    source=Source.APPLE_CALENDAR,
                    title=summary,
                    start=to_datetime(start_val) or start,
                    end=to_datetime(dtend_raw.dt) if dtend_raw else None,
                    all_day=is_all_day(start_val),
                    location=str(location) if location else None,
                    calendar_name=cal_name,
                ))
    return events
