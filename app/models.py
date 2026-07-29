"""Normalized data models shared across all connectors.

Every connector (Apple Calendar, Gmail, Canvas) returns data shaped into
these common models, so the frontend and the briefing agent don't need to
know which backend a given item came from.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def _ensure_aware(value: Optional[datetime]) -> Optional[datetime]:
    """Different sources disagree on whether their datetimes carry timezone
    info (Apple/CalDAV events usually do; our demo data usually doesn't).
    Normalize everything to timezone-aware UTC at the model boundary so
    nothing downstream — sorting, the briefing agent, "is this today" checks
    — ever has to guess, and so mixing sources in one sorted() call never
    raises "can't compare offset-naive and offset-aware datetimes" again."""
    if value is None:
        return value
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class Source(str, Enum):
    APPLE_CALENDAR = "apple_calendar"
    GMAIL = "gmail"
    CANVAS = "canvas"
    WEATHER = "weather"


class CalendarEvent(BaseModel):
    id: str
    source: Source
    title: str
    start: datetime
    end: Optional[datetime] = None
    all_day: bool = False
    location: Optional[str] = None
    calendar_name: Optional[str] = None

    _normalize = field_validator("start", "end", mode="after")(_ensure_aware)


class EmailItem(BaseModel):
    id: str
    source: Source
    subject: str
    sender: str
    received_at: datetime
    snippet: str = ""
    unread: bool = True
    needs_reply: bool = False
    priority: str = "normal"  # "urgent" | "normal" | "low"

    _normalize = field_validator("received_at", mode="after")(_ensure_aware)


class Assignment(BaseModel):
    id: str
    course_name: str
    title: str
    due_at: Optional[datetime] = None
    points_possible: Optional[float] = None
    submitted: bool = False
    url: Optional[str] = None

    _normalize = field_validator("due_at", mode="after")(_ensure_aware)


class WeatherInfo(BaseModel):
    """A single current-conditions snapshot, not a list — there's only ever
    one weather for "here" at a time, unlike calendar events/emails/assignments."""
    location: str
    temperature_f: float
    feels_like_f: Optional[float] = None
    high_f: Optional[float] = None
    low_f: Optional[float] = None
    condition: str = ""
    icon: str = ""  # a single emoji, so the frontend needs no icon assets


class SourceStatus(BaseModel):
    """Per-connector run metadata — this is what powers the efficiency story:
    each agent's wall-clock time, whether it actually ran, and why not."""
    source: Source
    ok: bool
    configured: bool
    duration_ms: float = 0.0
    item_count: int = 0
    error: Optional[str] = None
    demo: bool = False


class DashboardResult(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    events: List[CalendarEvent] = Field(default_factory=list)
    emails: List[EmailItem] = Field(default_factory=list)
    assignments: List[Assignment] = Field(default_factory=list)
    weather: Optional[WeatherInfo] = None
    briefing: Optional[str] = None
    statuses: List[SourceStatus] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    sequential_estimate_ms: float = 0.0

    @property
    def speedup(self) -> float:
        if self.total_duration_ms <= 0:
            return 1.0
        return round(self.sequential_estimate_ms / self.total_duration_ms, 2)


class TodoItem(BaseModel):
    """Local, user-entered to-do items. Unlike everything else in this file,
    these don't come from any external connector — they're persisted
    server-side (see todo_store.py) so they survive closing the browser tab
    or restarting the server, not just kept in page memory."""
    id: str
    text: str
    done: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    _normalize = field_validator("created_at", mode="after")(_ensure_aware)
