"""Shared helpers for connectors."""
from __future__ import annotations

import random
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Iterator, Optional

from ..models import SourceStatus, Source


@contextmanager
def timed() -> Iterator[dict]:
    """Usage: with timed() as t: ... ; t['ms'] holds elapsed milliseconds."""
    start = time.perf_counter()
    box = {"ms": 0.0}
    try:
        yield box
    finally:
        box["ms"] = (time.perf_counter() - start) * 1000.0


def simulate_latency(low: float = 0.6, high: float = 1.8) -> None:
    """Sleep a random realistic amount, used only in demo mode so the
    parallel-vs-sequential timing comparison stays meaningful even without
    real network calls."""
    time.sleep(random.uniform(low, high))


def default_window(days_ahead: int = 14) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    start = now - timedelta(days=1)
    end = now + timedelta(days=days_ahead)
    return start, end


def status_ok(source: Source, count: int, ms: float, demo: bool, configured: bool) -> SourceStatus:
    return SourceStatus(
        source=source, ok=True, configured=configured, duration_ms=round(ms, 1),
        item_count=count, demo=demo,
    )


def status_error(source: Source, ms: float, configured: bool, error: str) -> SourceStatus:
    return SourceStatus(
        source=source, ok=False, configured=configured, duration_ms=round(ms, 1),
        item_count=0, error=error, demo=False,
    )


def to_datetime(value) -> Optional[datetime]:
    """Normalize an icalendar dt value (date or datetime) to datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return None


def is_all_day(value) -> bool:
    return value is not None and not isinstance(value, datetime) and isinstance(value, date)
