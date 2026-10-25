"""Recognise the monthly whoishiring threads by title."""

from __future__ import annotations

import re
from dataclasses import dataclass

MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]

_MONTH = r"\((?P<month>[A-Za-z]+),? (?P<year>\d{4})\)"
PATTERNS = {
    "hiring": re.compile(rf"^Ask HN: Who is hiring\? {_MONTH}$", re.I),
    "seeking": re.compile(rf"^Ask HN: Who wants to be hired\? {_MONTH}$", re.I),
    "freelancer": re.compile(rf"^Ask HN: Freelancer\? Seeking freelancers?\? {_MONTH}$", re.I),
}
KINDS = tuple(PATTERNS)


@dataclass(frozen=True)
class Thread:
    kind: str
    month: str  # YYYY-MM, taken from the title
    id: int
    time: int  # unix seconds
    kids: int  # Firebase len(kids): every top-level comment ever made, incl. deleted and dead


def classify(title: str) -> tuple[str, str] | None:
    """Return (kind, YYYY-MM) for a monthly thread title, or None."""
    title = title.strip()
    for kind, pattern in PATTERNS.items():
        m = pattern.match(title)
        if not m:
            continue
        name = m.group("month").lower()
        if name not in MONTHS:
            return None
        return kind, f"{m.group('year')}-{MONTHS.index(name) + 1:02d}"
    return None
