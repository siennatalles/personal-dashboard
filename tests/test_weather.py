"""Weather connector: demo fallback, lat/lon shortcut, geocoding + forecast
parsing, and error handling. All HTTP calls are mocked — Open-Meteo needs no
API key, but we still shouldn't hit the real network in tests."""
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.connectors import weather
from app.models import Source


def test_demo_fallback_when_not_configured():
    settings = Settings(demo_mode=False, weather_location="")
    info, status = weather.fetch(settings)
    assert status.demo is True
    assert info is not None
    assert info.location
    assert info.temperature_f is not None


FORECAST_RESPONSE = {
    "current": {"temperature_2m": 71.4, "apparent_temperature": 69.8, "weather_code": 2},
    "daily": {"temperature_2m_max": [78.0], "temperature_2m_min": [59.5]},
}


def test_real_fetch_with_lat_lon_skips_geocoding():
    settings = Settings(demo_mode=False, weather_location="38.63,-90.2")

    forecast_resp = MagicMock()
    forecast_resp.json.return_value = FORECAST_RESPONSE
    forecast_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=forecast_resp) as mock_get:
        info, status = weather.fetch(settings)

    assert status.ok is True
    mock_get.assert_called_once()  # no separate geocoding call
    assert info.temperature_f == 71.4
    assert info.high_f == 78.0
    assert info.low_f == 59.5
    assert info.condition == "Partly cloudy"
    assert info.icon == "⛅"
    assert info.location == "38.63,-90.2"


GEOCODE_RESPONSE = {
    "results": [{"latitude": 38.63, "longitude": -90.2, "name": "St. Louis",
                 "admin1": "Missouri", "country_code": "US"}],
}


def test_real_fetch_geocodes_city_name():
    settings = Settings(demo_mode=False, weather_location="St. Louis")

    geocode_resp = MagicMock()
    geocode_resp.json.return_value = GEOCODE_RESPONSE
    geocode_resp.raise_for_status.return_value = None

    forecast_resp = MagicMock()
    forecast_resp.json.return_value = FORECAST_RESPONSE
    forecast_resp.raise_for_status.return_value = None

    with patch("requests.get", side_effect=[geocode_resp, forecast_resp]) as mock_get:
        info, status = weather.fetch(settings)

    assert status.ok is True
    assert mock_get.call_count == 2
    assert info.location == "St. Louis, Missouri, US"


def test_real_fetch_surfaces_geocoding_failure():
    settings = Settings(demo_mode=False, weather_location="Nowhere Really")

    empty_resp = MagicMock()
    empty_resp.json.return_value = {"results": []}
    empty_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=empty_resp):
        info, status = weather.fetch(settings)

    assert info is None
    assert status.ok is False
    assert "Nowhere Really" in status.error


def test_real_fetch_surfaces_http_errors():
    settings = Settings(demo_mode=False, weather_location="38.63,-90.2")
    with patch("requests.get", side_effect=Exception("connection timed out")):
        info, status = weather.fetch(settings)
    assert info is None
    assert status.ok is False


def test_unknown_weather_code_falls_back_gracefully():
    settings = Settings(demo_mode=False, weather_location="38.63,-90.2")
    resp = MagicMock()
    resp.json.return_value = {
        "current": {"temperature_2m": 50.0, "apparent_temperature": 48.0, "weather_code": 9999},
        "daily": {"temperature_2m_max": [55.0], "temperature_2m_min": [40.0]},
    }
    resp.raise_for_status.return_value = None
    with patch("requests.get", return_value=resp):
        info, status = weather.fetch(settings)
    assert status.ok is True
    assert info.condition == "Unknown"
    assert info.icon == "🌡️"
