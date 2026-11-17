"""Shared fail-loud helpers for data-ingestion scripts.

Principle: an ingestion step that fetched nothing, fetched nothing for the
live season, or left its dataset stale must exit non-zero so CI goes red.
A warning that scrolls past in a green run is how xG went stale unnoticed.

Usage:
    from ingest_guard import Problems, check_fresh
    problems = Problems("xG ingest")
    problems.add("EPL 2026-27 returned 0 matches")
    problems.add(check_fresh(newest_date, today, max_age_days=14, active=True, label="xg_data.csv"))
    problems.exit_if_any()          # prints a banner + GitHub ::error:: annotations, exit(1)
"""

from __future__ import annotations

import os
import sys
from datetime import date


def _in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def annotate(level: str, title: str, msg: str) -> None:
    """Emit a GitHub Actions annotation (shows on the run summary page).
    No-op outside Actions. level: 'error' | 'warning' | 'notice'."""
    if _in_github_actions():
        # Annotations are single-line; newlines must be URL-encoded.
        print(f"::{level} title={title}::{msg.replace(chr(10), '%0A')}", flush=True)


def fail(title: str, msg: str, code: int = 1) -> None:
    """Print a loud error banner to stderr and exit non-zero."""
    bar = "!" * 70
    sys.stdout.flush()  # keep the banner after the step's normal output in CI logs
    print(f"\n{bar}\nERROR [{title}]\n{msg}\n{bar}", file=sys.stderr, flush=True)
    annotate("error", title, msg)
    sys.exit(code)


def check_fresh(newest: date | None, today: date, max_age_days: int,
                active: bool, label: str) -> str | None:
    """Return an error string if `newest` is missing or older than
    max_age_days while `active` (e.g. during a season), else None."""
    if newest is None:
        return f"STALE: {label} has no dated rows at all"
    age = (today - newest).days
    if active and age > max_age_days:
        return (f"STALE: newest row in {label} is {newest} "
                f"({age} days old, limit {max_age_days} during an active season)")
    return None


class Problems:
    """Collect failures during a run; exit non-zero at the end if any.

    Collecting (rather than exiting at the first problem) lets a script still
    write whatever good data it fetched, then fail the CI step."""

    def __init__(self, title: str):
        self.title = title
        self.items: list[str] = []

    def add(self, msg: str | None) -> None:
        if msg:
            self.items.append(msg)
            print(f"  !! {msg}", flush=True)

    def exit_if_any(self) -> None:
        if self.items:
            fail(self.title, "\n".join(f"- {m}" for m in self.items))
