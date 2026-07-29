"""FastAPI app: one JSON endpoint the frontend polls, plus the static
dashboard page itself, plus a small CRUD API for the persistent to-do list."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import todo_store
from .config import settings
from .connectors import weather as weather_connector
from .models import DashboardResult, SourceStatus, TodoItem, WeatherInfo
from .orchestrator import build_dashboard

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="Personal Dashboard")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    # No-cache so the browser always picks up the latest index.html on
    # reload rather than serving a stale cached copy after edits.
    return FileResponse(str(STATIC_DIR / "index.html"),
                         headers={"Cache-Control": "no-store"})


@app.get("/api/dashboard", response_model=DashboardResult)
async def api_dashboard() -> DashboardResult:
    return await build_dashboard(settings)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "demo_mode": settings.demo_mode}


# --- Weather: a standalone endpoint (rather than folding this into
# /api/dashboard) so switching the location dropdown on the frontend is
# cheap — it re-fetches only weather instead of re-running every connector. ---

class WeatherResponse(BaseModel):
    weather: Optional[WeatherInfo] = None
    status: SourceStatus


@app.get("/api/weather", response_model=WeatherResponse)
def api_weather(location: Optional[str] = None) -> WeatherResponse:
    active_settings = settings if not location else dataclasses.replace(settings, weather_location=location)
    info, status = weather_connector.fetch(active_settings)
    return WeatherResponse(weather=info, status=status)


# --- To-do list: server-side persisted, survives closing the tab/browser or
# restarting the server (see app/todo_store.py) ---

class TodoCreate(BaseModel):
    text: str


class TodoUpdate(BaseModel):
    text: Optional[str] = None
    done: Optional[bool] = None


class TodoReorder(BaseModel):
    order: List[str]  # todo ids in the new display order


@app.get("/api/todos", response_model=List[TodoItem])
def api_list_todos() -> List[TodoItem]:
    return todo_store.list_todos()


@app.post("/api/todos", response_model=TodoItem)
def api_create_todo(payload: TodoCreate) -> TodoItem:
    if not payload.text.strip():
        raise HTTPException(400, "Todo text can't be empty")
    return todo_store.add_todo(payload.text)


@app.patch("/api/todos/{todo_id}", response_model=TodoItem)
def api_update_todo(todo_id: str, payload: TodoUpdate) -> TodoItem:
    item = todo_store.update_todo(todo_id, text=payload.text, done=payload.done)
    if item is None:
        raise HTTPException(404, "Todo not found")
    return item


@app.delete("/api/todos/{todo_id}")
def api_delete_todo(todo_id: str) -> dict:
    if not todo_store.delete_todo(todo_id):
        raise HTTPException(404, "Todo not found")
    return {"ok": True}


@app.put("/api/todos/reorder", response_model=List[TodoItem])
def api_reorder_todos(payload: TodoReorder) -> List[TodoItem]:
    return todo_store.reorder_todos(payload.order)
