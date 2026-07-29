"""Source connectors. Each module exposes a synchronous `fetch(settings)`
that returns `(items, SourceStatus)`. Connectors are synchronous (the
underlying libraries — caldav, requests, imaplib — are all blocking); the
orchestrator runs them concurrently via a thread pool so wall-clock time is
still dominated by the slowest connector, not the sum of all of them."""
