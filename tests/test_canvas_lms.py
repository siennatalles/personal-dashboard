"""Canvas connector: demo fallback + real-mode parsing incl. pagination."""
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.connectors import canvas_lms
from app.models import Source


def test_demo_fallback_when_not_configured():
    settings = Settings(demo_mode=False, canvas_base_url="", canvas_access_token="")
    items, status = canvas_lms.fetch(settings)
    assert status.demo is True
    assert len(items) > 0
    assert all(i.course_name for i in items)


PAGE_1 = [
    {
        "plannable_type": "assignment", "plannable_id": 1, "context_name": "CS 301",
        "plannable": {"title": "Problem Set 4", "due_at": "2026-07-24T23:59:00Z", "points_possible": 100},
        "submissions": {"submitted": False},
        "html_url": "/courses/1/assignments/1",
    },
    {
        # non-assignment planner items (e.g. announcements) should be filtered out
        "plannable_type": "announcement", "plannable_id": 2, "context_name": "CS 301",
        "plannable": {"title": "Class canceled"}, "submissions": False,
        "html_url": "/courses/1/announcements/2",
    },
]
PAGE_2 = [
    {
        "plannable_type": "quiz", "plannable_id": 3, "context_name": "ENGL 210",
        "plannable": {"title": "Reading quiz 6", "due_at": "2026-07-23T23:59:00Z", "points_possible": 10},
        "submissions": {"submitted": True},
        "html_url": "/courses/2/assignments/3",
    },
]


def test_real_fetch_follows_pagination_and_filters_types():
    settings = Settings(demo_mode=False, canvas_base_url="https://school.instructure.com",
                         canvas_access_token="tok-123")

    resp1 = MagicMock()
    resp1.json.return_value = PAGE_1
    resp1.links = {"next": {"url": "https://school.instructure.com/api/v1/planner/items?page=2"}}
    resp1.raise_for_status.return_value = None

    resp2 = MagicMock()
    resp2.json.return_value = PAGE_2
    resp2.links = {}
    resp2.raise_for_status.return_value = None

    with patch("requests.get", side_effect=[resp1, resp2]) as mock_get:
        items, status = canvas_lms.fetch(settings)

    assert status.ok is True
    assert mock_get.call_count == 2
    # first call carries the auth header
    _, kwargs = mock_get.call_args_list[0]
    assert kwargs["headers"]["Authorization"] == "Bearer tok-123"

    assert len(items) == 2  # announcement filtered out
    titles = {i.title for i in items}
    assert titles == {"Problem Set 4", "Reading quiz 6"}

    quiz = next(i for i in items if i.title == "Reading quiz 6")
    assert quiz.submitted is True
    assert quiz.course_name == "ENGL 210"


def test_real_fetch_surfaces_http_errors():
    settings = Settings(demo_mode=False, canvas_base_url="https://school.instructure.com",
                         canvas_access_token="bad-token")
    with patch("requests.get", side_effect=Exception("401 Unauthorized")):
        items, status = canvas_lms.fetch(settings)
    assert items == []
    assert status.ok is False
