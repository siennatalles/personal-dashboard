# Personal Dashboard

A daily dashboard that pulls from Apple Calendar, Gmail, Canvas, and local
weather, run through independent agents **in parallel**, with an
AI-written daily briefing on top.

## Why this exists

I've tried a lot of different productivity apps, but none of them had the
exact combination of features I wanted, so I decided to build a custom
dashboard instead — one that pulls from the specific sources I actually
check every day, laid out the way I want to see them, rather than adapting
my routine to whatever an existing app supported. It was also a chance to
get hands-on experience with AI agents and prompting, and with wiring up
and managing real API keys (Apple, Gmail, Canvas, Anthropic) across
different auth schemes rather than just reading about how they work.

Most integrations like this fetch each source one after another. This one
runs every connector concurrently on a thread pool and measures the actual
wall-clock difference — the dashboard shows you, in real numbers, how much
faster parallel execution is than doing it sequentially. That timing
comparison lives at the top of the page, not just in a README claim.

## Quick start (zero config)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 — with no `.env` file, everything runs in **demo
mode**: synthetic but realistic sample data, with simulated network latency
so the parallel-vs-sequential timing comparison stays meaningful even
offline. This is what you'd screenshot for a portfolio without exposing your
real data.

Recommended: double-click `Start Dashboard.command` instead of typing the
`uvicorn` command by hand — it starts the server (with `--reload`, so future
edits apply automatically) and opens your browser to the dashboard.

## Connecting your real accounts

Copy `.env.example` to `.env` and set `DEMO_MODE=false` once you've filled in
whichever sources you want live — anything left blank just falls back to
demo data for that one widget, the rest of the dashboard keeps working.

### Apple Calendar (CalDAV)
Apple has no OAuth API for Calendar — CalDAV is the only third-party path.
1. On your iPhone/Mac: **Settings → [your name] → Sign-In & Security →
   App-Specific Passwords → Generate** (requires 2FA on your Apple ID).
2. Set `APPLE_ID` and `APPLE_APP_SPECIFIC_PASSWORD` in `.env`.

### Gmail (IMAP)
Personal Gmail accounts only — Google Workspace disabled IMAP app-password
auth in 2025, so this won't work for a school/work Google account.
1. Enable 2-Step Verification on your Google account.
2. Generate an app password at https://myaccount.google.com/apppasswords.
3. Set `GMAIL_ADDRESS` and `GMAIL_APP_PASSWORD` in `.env`.

### Canvas LMS
1. Log into your school's Canvas → **Account → Settings → Approved
   Integrations → "+ New Access Token"**.
2. Set `CANVAS_BASE_URL` (e.g. `https://yourschool.instructure.com`) and
   `CANVAS_ACCESS_TOKEN` in `.env`.

### Weather
The only integration here that needs zero setup — Open-Meteo has no API key
or account at all.
1. Set `WEATHER_LOCATION` in `.env` to a city (e.g. `St. Louis, MO`) or a
   `lat,lon` pair to skip the geocoding lookup. This is just the default —
   the dashboard's weather card also has a dropdown (St. Louis, NYC, Short
   Hills NJ) that overrides it per-request via `GET /api/weather?location=`.

### AI daily briefing (optional)
Powers the short narrative summary at the top of the page ("Today: 3 events,
1 urgent email..."). Without a key, it falls back to a simple rule-based
(non-AI) version of the same summary — nothing breaks either way.
1. Get a key at https://console.anthropic.com.
2. Set `ANTHROPIC_API_KEY` in `.env`.

## Architecture

```
app/
  connectors/        one module per source, each exposing fetch(settings) -> (items, status)
    apple_calendar.py    CalDAV (caldav.icloud.com)
    gmail_imap.py          IMAP (imap.gmail.com)
    canvas_lms.py            REST API (personal access token)
    weather.py               Open-Meteo geocoding + forecast (no API key)
  orchestrator.py     runs every active connector concurrently via asyncio.to_thread,
                       measures wall-clock time vs. the summed sequential estimate
  briefing.py         synthesizes the daily narrative (AI if configured, rule-based fallback)
  todo_store.py        file-backed to-do persistence (data/todos.json) — survives closing
                        the tab/browser or restarting the server, not just page memory
  demo_data.py         synthetic data + simulated latency for zero-config demo mode
  main.py              FastAPI app: GET /api/dashboard, GET /api/weather, CRUD /api/todos,
                       serves static/index.html
static/index.html    single-file frontend, two independent columns (not a synced grid, so
                      the right column's cards stack at their own height instead of
                      stretching to match Calendar's) — left: Calendar + Email; right:
                      To-Do (capped height, drag-to-reorder), Weather (with a location
                      dropdown), Canvas. Calendar events are grouped by day, filtered to
                      the current week, with "Today" highlighted and past events struck
                      through; emails show read/unread
tests/                47 tests covering every connector's real-mode logic (mocked
                      HTTP/CalDAV/IMAP) and the to-do/weather API — no live credentials needed
data/
  todos.json            auto-created on first use — your to-do list lives here
```

Every connector follows the same shape: check if it's configured, fall back
to demo data with simulated latency if not, otherwise hit the real API and
normalize the result into shared models (`app/models.py`) — so the frontend,
the briefing agent, and the timing dashboard never need to know which source
an item came from.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

All 47 tests run without any real credentials — every external call (CalDAV,
IMAP, Canvas REST, Open-Meteo, Anthropic) is mocked, and the to-do store/API
tests use a temp file instead of your real data/todos.json, so the tests
verify the logic in isolation without touching real data.

## Roadmap

This is the first phase of a two-phase project. Next: package this as a
proper standalone deployment (currently it's a local dev server) — but the
integration logic here is exactly what a hosted version would reuse.
