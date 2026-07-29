# Personal Dashboard

FastAPI app pulling Apple Calendar, Gmail, Canvas, and weather concurrently,
with an AI daily briefing. See [README.md](README.md) for architecture and
[GETTING_STARTED.md](GETTING_STARTED.md) for setup.

## Git workflow

This repo is public on GitHub at `siennatalles/personal-dashboard` and is
linked from the user's GitHub profile README as a portfolio project — treat
it as user-facing.

- Always run `git pull origin main` before making any local edits or
  commits. Other tools (e.g. Claude Cowork) may push directly to this repo
  outside of Claude Code sessions, so local can silently fall behind — pull
  first to avoid divergent-history conflicts.
- After making changes, commit them with a clear message describing the
  change — don't leave edits sitting uncommitted.
- Always ask for explicit confirmation before running `git push`. Never push
  automatically, even after committing.
- Never commit `.env` or `data/todos.json` — both are gitignored (real
  credentials and the user's personal to-do data, respectively). If a change
  ever stages either of those, stop and flag it instead of committing.
- Prefer small, focused commits over batching unrelated changes together.
