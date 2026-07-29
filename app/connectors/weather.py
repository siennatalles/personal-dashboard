"""Weather via Open-Meteo — no API key or account needed at all, unlike
every other integration in this project. Two calls: geocode a plain city
name to lat/lon (skipped if WEATHER_LOCATION is already "lat,lon"), then
pull current conditions + today's high/low from the forecast endpoint.

Setup: set WEATHER_LOCATION in .env to a city (e.g. "St. Louis, MO") or a
"lat,lon" pair to skip geocoding.
"""
from __future__ import annotations

from typing import Optional, Tuple

import requests

from ..config import Settings
from ..demo_data import demo_weather
from ..models import Source, SourceStatus, WeatherInfo
from .common import simulate_latency, status_error, status_ok, timed

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes -> (description, emoji). Open-Meteo
# returns these as plain integers; this is the only translation needed.
_WMO_CODES = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Fog", "🌫️"),
    48: ("Depositing rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Dense drizzle", "🌦️"),
    56: ("Freezing drizzle", "🌧️"),
    57: ("Freezing drizzle", "🌧️"),
    61: ("Light rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    66: ("Freezing rain", "🌨️"),
    67: ("Freezing rain", "🌨️"),
    71: ("Light snow", "🌨️"),
    73: ("Snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    77: ("Snow grains", "❄️"),
    80: ("Light showers", "🌦️"),
    81: ("Showers", "🌦️"),
    82: ("Violent showers", "⛈️"),
    85: ("Snow showers", "🌨️"),
    86: ("Heavy snow showers", "❄️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with hail", "⛈️"),
    99: ("Thunderstorm with hail", "⛈️"),
}


def fetch(settings: Settings) -> Tuple[Optional[WeatherInfo], SourceStatus]:
    if settings.demo_mode or not settings.weather_configured:
        with timed() as t:
            simulate_latency()
            info = demo_weather()
        return info, status_ok(Source.WEATHER, 1, t["ms"],
                                demo=True, configured=settings.weather_configured)

    with timed() as t:
        try:
            info = _fetch_real(settings)
        except Exception as exc:  # noqa: BLE001
            return None, status_error(Source.WEATHER, t["ms"], True, str(exc))
    return info, status_ok(Source.WEATHER, 1, t["ms"], demo=False, configured=True)


def _fetch_real(settings: Settings) -> WeatherInfo:
    lat, lon, label = _resolve_location(settings.weather_location)

    resp = requests.get(FORECAST_URL, params={
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "auto",
    }, timeout=15)
    resp.raise_for_status()
    payload = resp.json()

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    code = current.get("weather_code")
    condition, icon = _WMO_CODES.get(code, ("Unknown", "🌡️"))

    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []

    return WeatherInfo(
        location=label,
        temperature_f=current.get("temperature_2m"),
        feels_like_f=current.get("apparent_temperature"),
        high_f=highs[0] if highs else None,
        low_f=lows[0] if lows else None,
        condition=condition,
        icon=icon,
    )


def _resolve_location(location: str) -> Tuple[float, float, str]:
    """Accepts either "lat,lon" (skips geocoding entirely) or a free-text
    place name (looked up via Open-Meteo's own geocoding endpoint, also
    free and keyless)."""
    parts = [p.strip() for p in location.split(",")]
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1]), location
        except ValueError:
            pass  # not a lat,lon pair — fall through to geocoding

    resp = requests.get(GEOCODE_URL, params={"name": location, "count": 1}, timeout=15)
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        raise ValueError(f"Couldn't find a location matching {location!r}")
    top = results[0]
    label = ", ".join(filter(None, [top.get("name"), top.get("admin1"), top.get("country_code")]))
    return top["latitude"], top["longitude"], label or location
