"""Daily briefing: a short narrative synthesized from everything the agents
pulled. Always works via a rule-based fallback (no API key needed); upgrades
to an AI-written version when ANTHROPIC_API_KEY is set, since that produces
noticeably more natural, prioritized prose than the template.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .config import Settings
from .models import DashboardResult


def build_briefing(result: DashboardResult, settings: Settings) -> str:
    fallback = _rule_based_briefing(result)
    if not settings.anthropic_configured:
        return fallback
    try:
        return _ai_briefing(result, settings) or fallback
    except Exception:
        return fallback


def _rule_based_briefing(result: DashboardResult) -> str:
    now = datetime.now(timezone.utc)
    today_events = [e for e in result.events if _is_today(e.start, now)]
    urgent_emails = [e for e in result.emails if e.priority == "urgent"]
    needs_reply = [e for e in result.emails if e.needs_reply]
    overdue = [a for a in result.assignments
               if a.due_at and not a.submitted and _to_aware(a.due_at) < now]
    due_soon = [a for a in result.assignments
                if a.due_at and not a.submitted and now <= _to_aware(a.due_at) <= now.replace(hour=23, minute=59)]

    parts = []
    if today_events:
        parts.append(f"{len(today_events)} event{'s' if len(today_events) != 1 else ''} on your calendar today")
    if urgent_emails:
        parts.append(f"{len(urgent_emails)} urgent email{'s' if len(urgent_emails) != 1 else ''}")
    elif needs_reply:
        parts.append(f"{len(needs_reply)} email{'s' if len(needs_reply) != 1 else ''} waiting on a reply")
    if overdue:
        parts.append(f"{len(overdue)} overdue assignment{'s' if len(overdue) != 1 else ''}")
    if due_soon:
        parts.append(f"{len(due_soon)} due today")

    if not parts:
        return "Nothing urgent on your plate right now — inbox, calendar, and coursework all look clear."
    return "Today: " + ", ".join(parts) + "."


def _ai_briefing(result: DashboardResult, settings: Settings) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    summary_input = {
        "events_today": [
            {"title": e.title, "start": e.start.isoformat(), "location": e.location}
            for e in result.events
        ][:15],
        "emails_needing_attention": [
            {"subject": e.subject, "sender": e.sender, "priority": e.priority}
            for e in result.emails if e.needs_reply or e.priority == "urgent"
        ][:15],
        "assignments_due": [
            {"title": a.title, "course": a.course_name,
             "due_at": a.due_at.isoformat() if a.due_at else None, "submitted": a.submitted}
            for a in result.assignments if not a.submitted
        ][:15],
        "weather": (
            {"condition": result.weather.condition, "temperature_f": result.weather.temperature_f,
             "high_f": result.weather.high_f, "low_f": result.weather.low_f}
            if result.weather else None
        ),
    }
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=250,
        messages=[{
            "role": "user",
            "content": (
                "Write a 2-3 sentence daily briefing for this person based on the "
                "JSON below. Be direct and specific (name the actual thing that's "
                "urgent, not just a count), warm but brief, no bullet points, no "
                "greeting/sign-off, plain text only.\n\n" + str(summary_input)
            ),
        }],
    )
    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    return text.strip()


def _to_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_today(dt: datetime, now: datetime) -> bool:
    dt = _to_aware(dt)
    return dt.date() == now.date()
