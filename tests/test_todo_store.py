"""Todo store: file-backed persistence, isolated from the real data/todos.json
via monkeypatching TODOS_PATH to a temp file for every test."""
import pytest

from app import todo_store


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(todo_store, "TODOS_PATH", tmp_path / "todos.json")


def test_starts_empty():
    assert todo_store.list_todos() == []


def test_add_and_list():
    item = todo_store.add_todo("Buy milk")
    assert item.text == "Buy milk"
    assert item.done is False
    assert item.id

    todos = todo_store.list_todos()
    assert len(todos) == 1
    assert todos[0].id == item.id


def test_persists_across_separate_reads():
    """Simulates surviving a server restart: nothing but the file on disk
    carries state between these two calls."""
    todo_store.add_todo("Task A")
    todo_store.add_todo("Task B")

    # a fresh list_todos() call re-reads from disk each time (no in-memory
    # cache), so this stands in for "close and reopen the app"
    todos = todo_store.list_todos()
    assert {t.text for t in todos} == {"Task A", "Task B"}


def test_update_toggles_done_and_edits_text():
    item = todo_store.add_todo("Original")
    updated = todo_store.update_todo(item.id, done=True)
    assert updated.done is True
    assert updated.text == "Original"  # unchanged

    updated2 = todo_store.update_todo(item.id, text="Edited")
    assert updated2.text == "Edited"
    assert updated2.done is True  # unaffected by a text-only update


def test_update_missing_id_returns_none():
    assert todo_store.update_todo("nonexistent", done=True) is None


def test_delete_removes_item():
    item = todo_store.add_todo("Temporary")
    assert todo_store.delete_todo(item.id) is True
    assert todo_store.list_todos() == []


def test_delete_missing_id_returns_false():
    assert todo_store.delete_todo("nonexistent") is False


def test_list_defaults_to_creation_order():
    a = todo_store.add_todo("First")
    b = todo_store.add_todo("Second")
    c = todo_store.add_todo("Third")
    todos = todo_store.list_todos()
    assert [t.id for t in todos] == [a.id, b.id, c.id]


def test_reorder_persists_new_order():
    a = todo_store.add_todo("First")
    b = todo_store.add_todo("Second")
    c = todo_store.add_todo("Third")

    result = todo_store.reorder_todos([c.id, a.id, b.id])
    assert [t.id for t in result] == [c.id, a.id, b.id]

    # re-read from disk to confirm it actually persisted, not just returned
    todos = todo_store.list_todos()
    assert [t.id for t in todos] == [c.id, a.id, b.id]


def test_reorder_ignores_unknown_ids():
    a = todo_store.add_todo("First")
    b = todo_store.add_todo("Second")

    result = todo_store.reorder_todos([b.id, "nonexistent", a.id])
    assert [t.id for t in result] == [b.id, a.id]


def test_reorder_appends_leftover_items_not_included():
    a = todo_store.add_todo("First")
    b = todo_store.add_todo("Second")
    c = todo_store.add_todo("Third")

    # only mention b and a — c is "leftover" and should be appended, not dropped
    result = todo_store.reorder_todos([b.id, a.id])
    assert [t.id for t in result] == [b.id, a.id, c.id]
