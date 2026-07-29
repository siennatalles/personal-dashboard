"""Orchestrator: verifies agents genuinely run concurrently (this is the
whole point of the project) and that results are assembled/sorted correctly."""
import asyncio
import time

import pytest

from app.config import Settings
from app import orchestrator
from app.models import Assignment, CalendarEvent, EmailItem, Source, SourceStatus, WeatherInfo


def _slow_fetch(delay, result, status):
    def _fn(settings):
        time.sleep(delay)
        return result, status
    return _fn


@pytest.mark.asyncio
async def test_connectors_run_concurrently(monkeypatch):
    """Four connectors each 'take' 0.3s. If they ran sequentially that's
    >=1.2s; run concurrently on a thread pool it should complete in well
    under 1s."""
    delay = 0.3
    empty_status = lambda src: SourceStatus(source=src, ok=True, configured=True,
                                             duration_ms=delay * 1000, item_count=0, demo=True)

    monkeypatch.setattr(orchestrator.apple_calendar, "fetch",
                         _slow_fetch(delay, [], empty_status(Source.APPLE_CALENDAR)))
    monkeypatch.setattr(orchestrator.gmail_imap, "fetch",
                         _slow_fetch(delay, [], empty_status(Source.GMAIL)))
    monkeypatch.setattr(orchestrator.canvas_lms, "fetch",
                         _slow_fetch(delay, [], empty_status(Source.CANVAS)))
    monkeypatch.setattr(orchestrator.weather, "fetch",
                         _slow_fetch(delay, None, empty_status(Source.WEATHER)))

    settings = Settings(demo_mode=True)
    start = time.perf_counter()
    result = await orchestrator.build_dashboard(settings)
    wall_clock = time.perf_counter() - start

    assert wall_clock < 1.0, f"connectors did not run concurrently (took {wall_clock:.2f}s)"
    assert result.sequential_estimate_ms == pytest.approx(delay * 1000 * 4, rel=0.1)
    assert result.speedup > 2  # ~4x in practice; assert conservatively for CI stability
    assert len(result.statuses) == 4


@pytest.mark.asyncio
async def test_results_are_merged_and_sorted(monkeypatch):
    from datetime import datetime

    e1 = CalendarEvent(id="a", source=Source.APPLE_CALENDAR, title="Later",
                        start=datetime(2026, 7, 22, 15, 0))
    e2 = CalendarEvent(id="b", source=Source.APPLE_CALENDAR, title="Earlier",
                        start=datetime(2026, 7, 22, 9, 0))
    em1 = EmailItem(id="x", source=Source.GMAIL, subject="Old", sender="a@a.com",
                     received_at=datetime(2026, 7, 20, 0, 0))
    em2 = EmailItem(id="y", source=Source.GMAIL, subject="New", sender="b@b.com",
                     received_at=datetime(2026, 7, 22, 0, 0))
    w = WeatherInfo(location="Testville", temperature_f=70.0, condition="Clear sky", icon="☀️")
    status = lambda src, n: SourceStatus(source=src, ok=True, configured=True,
                                          duration_ms=1, item_count=n, demo=True)

    monkeypatch.setattr(orchestrator.apple_calendar, "fetch",
                         lambda s: ([e1, e2], status(Source.APPLE_CALENDAR, 2)))
    monkeypatch.setattr(orchestrator.gmail_imap, "fetch",
                         lambda s: ([em1, em2], status(Source.GMAIL, 2)))
    monkeypatch.setattr(orchestrator.canvas_lms, "fetch",
                         lambda s: ([], status(Source.CANVAS, 0)))
    monkeypatch.setattr(orchestrator.weather, "fetch",
                         lambda s: (w, status(Source.WEATHER, 1)))

    result = await orchestrator.build_dashboard(Settings(demo_mode=True))

    assert [e.title for e in result.events] == ["Earlier", "Later"]
    assert [e.subject for e in result.emails] == ["New", "Old"]  # most recent first
    assert result.weather.location == "Testville"
    assert result.briefing  # briefing was synthesized from the merged data
