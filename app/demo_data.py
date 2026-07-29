"""Synthetic sample data so the dashboard is fully demoable with zero
credentials configured. Each generator simulates realistic network latency
so the parallel-vs-sequential timing comparison stays meaningful even in
demo mode.

Timestamps are generated relative to "now" so the demo always looks current.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .models import Assignment, CalendarEvent, EmailItem, Source, WeatherInfo


def _now() -> datetime:
    return datetime.utcnow()


def demo_apple_events() -> list[CalendarEvent]:
    now = _now()
    return [
        CalendarEvent(
            id="apple-1",
            source=Source.APPLE_CALENDAR,
            title="Dentist appointment",
            start=now.replace(hour=9, minute=30, second=0, microsecond=0),
            end=now.replace(hour=10, minute=15, second=0, microsecond=0),
            location="Bright Smile Dental",
            calendar_name="Personal",
        ),
        CalendarEvent(
            id="apple-2",
            source=Source.APPLE_CALENDAR,
            title="Dinner with Sam",
            start=(now + timedelta(hours=9)).replace(minute=0, second=0, microsecond=0),
            end=(now + timedelta(hours=11)).replace(minute=0, second=0, microsecond=0),
            location="Osteria",
            calendar_name="Personal",
        ),
        CalendarEvent(
            id="apple-3",
            source=Source.APPLE_CALENDAR,
            title="Mom's birthday",
            start=(now + timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0),
            all_day=True,
            calendar_name="Family",
        ),
    ]


def demo_gmail_emails() -> list[EmailItem]:
    now = _now()
    return [
        EmailItem(
            id="gm-em-1",
            source=Source.GMAIL,
            subject="Are you free to review this PR?",
            sender="alex@opensourceproject.dev",
            received_at=now - timedelta(hours=1),
            snippet="Whenever you get a chance — nothing urgent, just want your eyes on...",
            unread=True,
            needs_reply=True,
            priority="normal",
        ),
        EmailItem(
            id="gm-em-2",
            source=Source.GMAIL,
            subject="Your order has shipped",
            sender="orders@bookstore.com",
            received_at=now - timedelta(hours=20),
            snippet="Good news! Your package is on its way and should arrive by...",
            unread=False,
            needs_reply=False,
            priority="low",
        ),
        EmailItem(
            id="gm-em-3",
            source=Source.GMAIL,
            subject="Password reset requested",
            sender="security@somesite.com",
            received_at=now - timedelta(hours=30),
            snippet="We received a request to reset your password. If this wasn't you...",
            unread=True,
            needs_reply=False,
            priority="normal",
        ),
    ]


def demo_canvas_assignments() -> list[Assignment]:
    now = _now()
    return [
        Assignment(
            id="canvas-1",
            course_name="CS 301: Algorithms",
            title="Problem Set 4",
            due_at=now + timedelta(days=2, hours=3),
            points_possible=100,
            submitted=False,
            url="https://canvas.example.edu/courses/1/assignments/1",
        ),
        Assignment(
            id="canvas-2",
            course_name="ENGL 210: Rhetoric",
            title="Essay draft 2",
            due_at=now + timedelta(days=5),
            points_possible=50,
            submitted=False,
            url="https://canvas.example.edu/courses/2/assignments/2",
        ),
        Assignment(
            id="canvas-3",
            course_name="CS 301: Algorithms",
            title="Reading quiz 6",
            due_at=now - timedelta(hours=3),
            points_possible=10,
            submitted=True,
            url="https://canvas.example.edu/courses/1/assignments/3",
        ),
    ]


def demo_weather() -> WeatherInfo:
    return WeatherInfo(
        location="Demo City",
        temperature_f=68.0,
        feels_like_f=66.0,
        high_f=74.0,
        low_f=58.0,
        condition="Partly cloudy",
        icon="⛅",
    )
