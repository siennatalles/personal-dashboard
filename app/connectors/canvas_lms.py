"""Canvas LMS via its REST API and a personal access token.

Setup: log into your school's Canvas, go to Account > Settings > Approved
Integrations > "+ New Access Token". Set CANVAS_BASE_URL to your school's
Canvas domain (e.g. https://yourschool.instructure.com).

Uses the Planner API, which returns a unified feed of assignments/quizzes
across every course with due dates — exactly what a "what's due" widget needs,
rather than iterating every course's assignment list by hand.
"""
from __future__ import annotations

from typing import List, Tuple

import requests

from ..config import Settings
from ..demo_data import demo_canvas_assignments
from ..models import Assignment, Source, SourceStatus
from .common import default_window, simulate_latency, status_error, status_ok, timed


def fetch(settings: Settings) -> Tuple[List[Assignment], SourceStatus]:
    if settings.demo_mode or not settings.canvas_configured:
        with timed() as t:
            simulate_latency()
            items = demo_canvas_assignments()
        return items, status_ok(Source.CANVAS, len(items), t["ms"],
                                 demo=True, configured=settings.canvas_configured)

    with timed() as t:
        try:
            items = _fetch_real(settings)
        except Exception as exc:  # noqa: BLE001
            return [], status_error(Source.CANVAS, t["ms"], True, str(exc))
    return items, status_ok(Source.CANVAS, len(items), t["ms"], demo=False, configured=True)


def _fetch_real(settings: Settings) -> List[Assignment]:
    start, end = default_window()
    headers = {"Authorization": f"Bearer {settings.canvas_access_token}"}
    url = f"{settings.canvas_base_url}/api/v1/planner/items"
    params = {
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "per_page": "50",
    }

    out: List[Assignment] = []
    # Canvas paginates via a `Link` header — follow `next` until exhausted.
    while url:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        for item in resp.json():
            if item.get("plannable_type") not in ("assignment", "quiz"):
                continue
            plannable = item.get("plannable") or {}
            submissions = item.get("submissions") or {}
            out.append(Assignment(
                id=str(item.get("plannable_id")),
                course_name=item.get("context_name") or "Canvas",
                title=plannable.get("title") or "(untitled assignment)",
                due_at=plannable.get("due_at"),
                points_possible=plannable.get("points_possible"),
                submitted=bool(submissions.get("submitted")) if isinstance(submissions, dict) else False,
                url=item.get("html_url"),
            ))
        url = resp.links.get("next", {}).get("url")
        params = None  # `next` URL already includes query params
    return out
