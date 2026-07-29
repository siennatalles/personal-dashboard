"""Runs every connector concurrently and assembles a DashboardResult.

Each connector is synchronous (caldav/requests/imaplib are all blocking
libraries), so we run them on a thread pool via asyncio.to_thread and gather
the results — wall-clock time ends up dominated by the single slowest agent
rather than the sum of all of them, which is the whole efficiency point of
this project: independent I/O-bound calls run concurrently instead of one
after another.

`sequential_estimate_ms` (sum of each connector's own duration) makes that
concrete: it's what the same calls would have cost run one at a time,
without needing to actually re-run them sequentially and double real API usage.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from .briefing import build_briefing
from .config import Settings
from .connectors import apple_calendar, canvas_lms, gmail_imap, weather
from .models import DashboardResult

_FAR_FUTURE = datetime.max.replace(tzinfo=timezone.utc)


async def build_dashboard(settings: Settings) -> DashboardResult:
    start = time.perf_counter()

    (apple_events, apple_status), (gmail_items, gmail_status), \
        (assignments, canvas_status), (weather_info, weather_status) = await asyncio.gather(
        asyncio.to_thread(apple_calendar.fetch, settings),
        asyncio.to_thread(gmail_imap.fetch, settings),
        asyncio.to_thread(canvas_lms.fetch, settings),
        asyncio.to_thread(weather.fetch, settings),
    )

    total_ms = (time.perf_counter() - start) * 1000.0
    statuses = [apple_status, gmail_status, canvas_status, weather_status]
    sequential_estimate_ms = sum(s.duration_ms for s in statuses)

    events = sorted(apple_events, key=lambda e: e.start)
    emails = sorted(gmail_items, key=lambda e: e.received_at, reverse=True)
    # undated assignments (no due_at) sort last, via the far-future sentinel —
    # avoids comparing None to a datetime, which raises just like mixing
    # naive/aware datetimes does.
    assignments_sorted = sorted(assignments, key=lambda a: a.due_at or _FAR_FUTURE)

    result = DashboardResult(
        events=events,
        emails=emails,
        assignments=assignments_sorted,
        weather=weather_info,
        statuses=statuses,
        total_duration_ms=round(total_ms, 1),
        sequential_estimate_ms=round(sequential_estimate_ms, 1),
    )
    result.briefing = build_briefing(result, settings)
    return result
