"""Turn the whoishiring threads into the monthly dataset under data/."""

from __future__ import annotations

import csv
import io
import json
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import skills
from .fetch import ALGOLIA, FIREBASE, FRED_CSV, FetchError, Fetcher
from .threads import Thread, classify

# `_whoishiring` stood in for the main account in April and May 2015.
ACCOUNTS = ("whoishiring", "_whoishiring")
OPEN_DAYS = 14  # HN closes threads to new comments after two weeks
DAY = 86400

METHOD = {
    "ratio_all": "Who wants to be hired? top-level comments / Who is hiring? top-level comments, "
    "counting every top-level comment id in the Firebase item's `kids` (includes deleted and dead).",
    "ratio_visible": "Same, counting only top-level comments still visible today "
    "(Algolia items API `children` with text and author; equals kids minus deleted minus dead).",
    "skills": "One regex per skill over visible comment text; a comment counts once per skill. "
    "seekers_per_job_3m = seeking hits / hiring hits summed over the month and the two before it. "
    "Seeker posts list long 'Technologies:' stacks, so compare skills with each other, not with the overall ratio.",
    "jolts": "FRED JTSJOL (JOLTS job openings, SA, thousands) / FRED UNEMPLOY (CPS unemployed, SA, thousands).",
    "complete": "False while either thread is younger than 14 days.",
}


class BuildError(RuntimeError):
    pass


@dataclass
class Visible:
    count: int
    skill_hits: Counter = field(default_factory=Counter)


def _item(fetcher: Fetcher, item_id: int, now: float, freeze_days: int):
    url, key = f"{FIREBASE}/item/{item_id}.json", f"firebase/item/{item_id}.json"
    was_cached = fetcher.has(key)
    item = fetcher.get_json(url, key)
    if was_cached and not fetcher.offline and _recent(item, now, freeze_days):
        item = fetcher.get_json(url, key, fresh=True)
    return item


def _recent(item, now: float, freeze_days: int) -> bool:
    return not item or now - item.get("time", 0) < freeze_days * DAY


def collect_threads(fetcher: Fetcher, now: float, freeze_days: int = 30):
    """Return ({(kind, month): Thread}, skipped rows)."""
    submitted = []
    for account in ACCOUNTS:
        user = fetcher.get_json(f"{FIREBASE}/user/{account}.json", f"firebase/user-{account}.json", fresh=True)
        if not user or "submitted" not in user:
            raise BuildError(f"Firebase user/{account} returned no 'submitted' list")
        submitted += user["submitted"]
    threads: dict[tuple[str, str], Thread] = {}
    skipped = []
    for item_id in submitted:
        item = _item(fetcher, item_id, now, freeze_days)
        if not item:
            skipped.append({"id": item_id, "title": "", "date": "", "reason": "missing"})
            continue
        title = item.get("title") or ""
        date = datetime.fromtimestamp(item.get("time", 0), timezone.utc).strftime("%Y-%m-%d")
        reason = None
        if item.get("type") != "story":
            reason = f"type {item.get('type')}"
        elif item.get("deleted"):
            reason = "deleted"
        elif item.get("dead"):
            reason = "dead"
        found = classify(title) if reason is None else None
        if reason is None and found is None:
            reason = "not a monthly thread title"
        if reason:
            skipped.append({"id": item_id, "title": title, "date": date, "reason": reason})
            continue
        kind, month = found
        if (kind, month) in threads:
            other = threads[(kind, month)]
            raise BuildError(f"two {kind} threads for {month}: {other.id} and {item_id}")
        threads[(kind, month)] = Thread(kind, month, item_id, item["time"], len(item.get("kids") or []))
    return threads, skipped


def visible(fetcher: Fetcher, thread: Thread, now: float, freeze_days: int = 30) -> Visible:
    url, key = f"{ALGOLIA}/items/{thread.id}", f"algolia/items/{thread.id}.json"
    fresh = now - thread.time < freeze_days * DAY
    tree = fetcher.get_json(url, key, fresh=fresh)
    if not tree or "children" not in tree:
        raise BuildError(f"Algolia items/{thread.id} has no children list")
    result = Visible(0)
    for child in tree["children"]:
        if not (child.get("text") and child.get("author")):
            continue
        result.count += 1
        result.skill_hits.update(skills.match(child["text"]))
    return result


def _months(first: str, last: str) -> list[str]:
    y, m = map(int, first.split("-"))
    out = []
    while f"{y}-{m:02d}" <= last:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _ratio(num: int | None, den: int | None) -> float | None:
    if num is None or not den:
        return None
    return round(num / den, 2)


def monthly_rows(threads, vis: dict[int, Visible], since: str, now: float) -> list[dict]:
    last = max(month for _, month in threads)
    rows = []
    for month in _months(since, last):
        h, s, f = (threads.get((k, month)) for k in ("hiring", "seeking", "freelancer"))
        hv = vis.get(h.id) if h else None
        sv = vis.get(s.id) if s else None
        complete = bool(h and s) and now - max(h.time, s.time) >= OPEN_DAYS * DAY
        rows.append({
            "month": month,
            "hiring_id": h.id if h else None,
            "seeking_id": s.id if s else None,
            "freelancer_id": f.id if f else None,
            "hiring_all": h.kids if h else None,
            "seeking_all": s.kids if s else None,
            "ratio_all": _ratio(s and s.kids, h and h.kids),
            "hiring_visible": hv.count if hv else None,
            "seeking_visible": sv.count if sv else None,
            "ratio_visible": _ratio(sv and sv.count, hv and hv.count),
            "freelancer_all": f.kids if f else None,
            "complete": complete,
        })
    return rows


def skill_rows(rows: list[dict], vis: dict[int, Visible]) -> list[dict]:
    out = []
    for i, row in enumerate(rows):
        if row["hiring_visible"] is None or row["seeking_visible"] is None:
            continue
        window = rows[max(0, i - 2): i + 1]
        full = len(window) == 3 and all(w["hiring_visible"] is not None and w["seeking_visible"] is not None for w in window)
        for name in skills.SKILLS:
            h = vis[row["hiring_id"]].skill_hits[name]
            s = vis[row["seeking_id"]].skill_hits[name]
            rec = {"month": row["month"], "skill": name, "hiring_hits": h, "seeking_hits": s,
                   "hiring_hits_3m": None, "seeking_hits_3m": None, "seekers_per_job_3m": None}
            if full:
                h3 = sum(vis[w["hiring_id"]].skill_hits[name] for w in window)
                s3 = sum(vis[w["seeking_id"]].skill_hits[name] for w in window)
                rec.update(hiring_hits_3m=h3, seeking_hits_3m=s3, seekers_per_job_3m=_ratio(s3, h3))
            out.append(rec)
    return out


def jolts_rows(fetcher: Fetcher, since: str) -> list[dict]:
    body = fetcher.get(FRED_CSV, "fred/jolts.csv", fresh=True).decode("utf-8")
    reader = csv.DictReader(io.StringIO(body))
    need = {"observation_date", "JTSJOL", "UNEMPLOY"}
    if not reader.fieldnames or not need <= set(reader.fieldnames):
        raise BuildError(f"FRED CSV columns {reader.fieldnames} lack {sorted(need)}")
    rows = []
    for rec in reader:
        month = rec["observation_date"][:7]
        if month < since or not rec["JTSJOL"] or not rec["UNEMPLOY"]:
            continue
        openings, unemployed = float(rec["JTSJOL"]), float(rec["UNEMPLOY"])
        rows.append({"month": month, "openings_k": openings, "unemployed_k": unemployed,
                     "openings_per_unemployed": round(openings / unemployed, 2)})
    if not rows:
        raise BuildError("FRED CSV had no JOLTS rows in range")
    return rows


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: ("" if row.get(k) is None else str(row[k]).lower() if isinstance(row[k], bool) else row[k]) for k in fields})


def summary(rows: list[dict], top: int = 5) -> dict:
    done = [r for r in rows if r["complete"] and r["ratio_all"] is not None]
    if not done:
        raise BuildError("no complete month with both threads")
    latest = done[-1]
    highest = sorted(done, key=lambda r: (-r["ratio_all"], r["month"]))[:top]
    current = rows[-1] if not rows[-1]["complete"] else None
    return {"latest_complete": latest, "highest": highest, "in_progress": current}


def build(fetcher: Fetcher, out: Path, *, since: str = "2014-07", with_jolts: bool = False,
          freeze_days: int = 30, now: float | None = None, log=lambda _m: None) -> dict:
    now = time.time() if now is None else now
    threads, skipped = collect_threads(fetcher, now, freeze_days)
    log(f"{len(threads)} monthly threads, {len(skipped)} other submissions")
    vis: dict[int, Visible] = {}
    for (kind, month), thread in sorted(threads.items(), key=lambda kv: kv[0][1]):
        if kind in ("hiring", "seeking") and month >= since:
            vis[thread.id] = visible(fetcher, thread, now, freeze_days)
    rows = monthly_rows(threads, vis, since, now)
    srows = skill_rows(rows, vis)
    jrows = jolts_rows(fetcher, since) if with_jolts else []

    out.mkdir(parents=True, exist_ok=True)
    _write_csv(out / "monthly.csv", rows, list(rows[0]))
    _write_csv(out / "skills.csv", srows, ["month", "skill", "hiring_hits", "seeking_hits",
                                           "hiring_hits_3m", "seeking_hits_3m", "seekers_per_job_3m"])
    _write_csv(out / "skipped.csv", skipped, ["id", "title", "date", "reason"])
    if with_jolts:
        _write_csv(out / "jolts.csv", jrows, ["month", "openings_k", "unemployed_k", "openings_per_unemployed"])
    doc = {
        "generated_at": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": METHOD,
        "summary": summary(rows),
        "monthly": rows,
        "skills": srows,
        "jolts": jrows,
    }
    (out / "hn-glut.json").write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    log(f"{fetcher.requests} HTTP requests")
    return doc


__all__ = ["build", "BuildError", "FetchError", "summary"]
