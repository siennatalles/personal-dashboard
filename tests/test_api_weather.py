"""/api/weather: the standalone endpoint the location dropdown calls,
independent of the main /api/dashboard fetch."""
from fastapi.testclient import TestClient

from app import main
from app.config import Settings
from app.models import Source, SourceStatus, WeatherInfo


def _fake_fetch(location_seen):
    def _fn(settings):
        location_seen.append(settings.weather_location)
        return (
            WeatherInfo(location=settings.weather_location or "Demo City",
                        temperature_f=72.0, condition="Clear sky", icon="☀️"),
            SourceStatus(source=Source.WEATHER, ok=True, configured=True,
                         duration_ms=5, item_count=1, demo=False),
        )
    return _fn


def test_weather_endpoint_uses_query_param_location(monkeypatch):
    seen = []
    monkeypatch.setattr(main.weather_connector, "fetch", _fake_fetch(seen))
    client = TestClient(main.app)

    resp = client.get("/api/weather", params={"location": "Short Hills, NJ"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["weather"]["location"] == "Short Hills, NJ"
    assert data["status"]["ok"] is True
    assert seen == ["Short Hills, NJ"]


def test_weather_endpoint_falls_back_to_server_default_without_location(monkeypatch):
    seen = []
    monkeypatch.setattr(main.weather_connector, "fetch", _fake_fetch(seen))
    monkeypatch.setattr(main, "settings", Settings(weather_location="St. Louis, MO"))
    client = TestClient(main.app)

    resp = client.get("/api/weather")
    assert resp.status_code == 200
    assert seen == ["St. Louis, MO"]
