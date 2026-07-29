"""File-backed persistence for the to-do list.

Deliberately not localStorage/in-memory: the whole point is that items
survive closing the tab, quitting the browser, or restarting the server —
so every change is written straight to disk (data/todos.json) instead of
living only in page or process memory. A thread lock guards read-modify-write
so two near-simultaneous requests (e.g. two browser tabs) can't clobber each
other's writes.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from .config import ROOT
from .models import TodoItem

TODOS_PATH = ROOT / "data" / "todos.json"
_lock = threading.Lock()


def _ensure_file() -> None:
    TODOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not TODOS_PATH.exists():
        TODOS_PATH.write_text("[]")


def _read_raw() -> List[TodoItem]:
    _ensure_file()
    raw = json.loads(TODOS_PATH.read_text() or "[]")
    return [TodoItem(**item) for item in raw]


def _write_raw(todos: List[TodoItem]) -> None:
    TODOS_PATH.write_text(json.dumps(
        [json.loads(t.model_dump_json()) for t in todos], indent=2,
    ))


def list_todos() -> List[TodoItem]:
    # Display order is whatever order they're stored in the file — new
    # items are appended (so it starts out as creation order), and
    # reorder_todos() below rewrites the file to persist manual drag-reorders.
    # This is why we don't sort by created_at here anymore: doing so would
    # silently undo any reordering the user did.
    with _lock:
        return _read_raw()


def add_todo(text: str) -> TodoItem:
    text = text.strip()
    item = TodoItem(id=str(uuid.uuid4()), text=text, done=False,
                     created_at=datetime.now(timezone.utc))
    with _lock:
        todos = _read_raw()
        todos.append(item)
        _write_raw(todos)
    return item


def update_todo(todo_id: str, text: Optional[str] = None,
                 done: Optional[bool] = None) -> Optional[TodoItem]:
    with _lock:
        todos = _read_raw()
        for t in todos:
            if t.id == todo_id:
                if text is not None:
                    t.text = text.strip()
                if done is not None:
                    t.done = done
                _write_raw(todos)
                return t
    return None


def delete_todo(todo_id: str) -> bool:
    with _lock:
        todos = _read_raw()
        remaining = [t for t in todos if t.id != todo_id]
        if len(remaining) == len(todos):
            return False
        _write_raw(remaining)
    return True


def reorder_todos(ordered_ids: List[str]) -> List[TodoItem]:
    """Rewrite the file so items appear in `ordered_ids` order. Any existing
    todo whose id isn't in `ordered_ids` (e.g. a race with a concurrent add)
    is appended at the end rather than silently dropped."""
    with _lock:
        todos = _read_raw()
        by_id = {t.id: t for t in todos}
        new_order = [by_id[i] for i in ordered_ids if i in by_id]
        leftover = [t for t in todos if t.id not in ordered_ids]
        new_order.extend(leftover)
        _write_raw(new_order)
        return new_order
