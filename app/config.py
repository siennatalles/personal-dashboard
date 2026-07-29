"""Loads settings from .env (falling back to demo mode when unset)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    demo_mode: bool = _bool("DEMO_MODE", True)

    apple_id: str = os.getenv("APPLE_ID", "")
    apple_app_password: str = os.getenv("APPLE_APP_SPECIFIC_PASSWORD", "")

    gmail_address: str = os.getenv("GMAIL_ADDRESS", "")
    gmail_app_password: str = os.getenv("GMAIL_APP_PASSWORD", "")

    canvas_base_url: str = os.getenv("CANVAS_BASE_URL", "").rstrip("/")
    canvas_access_token: str = os.getenv("CANVAS_ACCESS_TOKEN", "")

    # A city name (e.g. "St. Louis, MO") or "lat,lon" — Open-Meteo needs no
    # API key at all, so this is the only thing to configure for weather.
    weather_location: str = os.getenv("WEATHER_LOCATION", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def apple_configured(self) -> bool:
        return bool(self.apple_id and self.apple_app_password)

    @property
    def gmail_configured(self) -> bool:
        return bool(self.gmail_address and self.gmail_app_password)

    @property
    def canvas_configured(self) -> bool:
        return bool(self.canvas_base_url and self.canvas_access_token)

    @property
    def weather_configured(self) -> bool:
        return bool(self.weather_location)

    @property
    def anthropic_configured(self) -> bool:
        return bool(self.anthropic_api_key)


settings = Settings()
