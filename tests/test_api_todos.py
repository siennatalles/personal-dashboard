"""To-do CRUD API endpoints, exercised through the actual FastAPI app."""
import pytest
from fastapi.testclient import TestClient

from app import todo_store
from app.main import app


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(todo_store, "TODOS_PATH", tmp_path / "todos.json")


@pytest.fixture
def client():
    return TestClient(app)


def test_list_starts_empty(client):
    resp = client.get("/api/todos")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_then_list(client):
    resp = client.post("/api/todos", json={"text": "Finish homework"})
    assert resp.status_code == 200
    created = resp.json()
    assert created["text"] == "Finish homework"
    assert created["done"] is False

    resp = client.get("/api/todos")
    assert len(resp.json()) == 1


def test_create_rejects_empty_text(client):
    resp = client.post("/api/todos", json={"text": "   "})
    assert resp.status_code == 400


def test_patch_toggles_done(client):
    created = client.post("/api/todos", json={"text": "Task"}).json()
    resp = client.patch(f"/api/todos/{created['id']}", json={"done": True})
    assert resp.status_code == 200
    assert resp.json()["done"] is True


def test_patch_missing_id_404s(client):
    resp = client.patch("/api/todos/does-not-exist", json={"done": True})
    assert resp.status_code == 404


def test_delete_removes_item(client):
    created = client.post("/api/todos", json={"text": "Task"}).json()
    resp = client.delete(f"/api/todos/{created['id']}")
    assert resp.status_code == 200
    assert client.get("/api/todos").json() == []


def test_delete_missing_id_404s(client):
    resp = client.delete("/api/todos/does-not-exist")
    assert resp.status_code == 404


def test_survives_across_requests_like_a_restart(client):
    """Each TestClient request goes through the real endpoint -> todo_store
    -> disk round trip, so two independent requests standing in for two
    separate page loads (or a server restart in between) still agree."""
    client.post("/api/todos", json={"text": "Persisted task"})
    resp = client.get("/api/todos")
    assert resp.json()[0]["text"] == "Persisted task"


def test_reorder_endpoint_persists_new_order(client):
    a = client.post("/api/todos", json={"text": "First"}).json()
    b = client.post("/api/todos", json={"text": "Second"}).json()
    c = client.post("/api/todos", json={"text": "Third"}).json()

    resp = client.put("/api/todos/reorder", json={"order": [c["id"], a["id"], b["id"]]})
    assert resp.status_code == 200
    assert [t["id"] for t in resp.json()] == [c["id"], a["id"], b["id"]]

    # confirm it stuck, not just returned in the response
    listed = client.get("/api/todos").json()
    assert [t["id"] for t in listed] == [c["id"], a["id"], b["id"]]
