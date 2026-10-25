"""hn-glut command line."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from .build import BuildError, build, summary
from .fetch import FetchError, Fetcher


def _show(out: Path) -> int:
    path = out / "monthly.csv"
    if not path.exists():
        print(f"hn-glut: {path} not found; run `hn-glut build` first", file=sys.stderr)
        return 1
    rows = []
    with path.open() as fh:
        for rec in csv.DictReader(fh):
            rows.append({
                **rec,
                "ratio_all": float(rec["ratio_all"]) if rec["ratio_all"] else None,
                "complete": rec["complete"] == "true",
            })
    s = summary(rows)
    _print_summary(s)
    return 0


def _fmt(row: dict) -> str:
    vis = f", visible {row['seeking_visible']}/{row['hiring_visible']} = {row['ratio_visible']}" if row.get("ratio_visible") else ""
    return f"{row['month']}: {row['seeking_all']}/{row['hiring_all']} = {row['ratio_all']}{vis}"


def _print_summary(s: dict) -> None:
    print("latest complete month  " + _fmt(s["latest_complete"]))
    if s["in_progress"] and s["in_progress"]["ratio_all"] is not None:
        print("in progress            " + _fmt(s["in_progress"]))
    print("highest seekers per job post since 2014:")
    for row in s["highest"]:
        print("  " + _fmt(row))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hn-glut", description="HN job seekers per job post, monthly since 2014.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="fetch (or reuse cache) and write the dataset")
    b.add_argument("--out", type=Path, default=Path("data"))
    b.add_argument("--cache", type=Path, default=Path(".cache"))
    b.add_argument("--since", default="2014-07", help="first month in the output, YYYY-MM (default 2014-07)")
    b.add_argument("--jolts", action="store_true", help="also fetch JOLTS openings per unemployed (FRED)")
    b.add_argument("--offline", action="store_true", help="use only cached responses; fail if one is missing")
    b.add_argument("--freeze-days", type=int, default=30, help="re-fetch threads younger than this (default 30)")
    b.add_argument("-v", "--verbose", action="store_true", help="log every request to stderr")
    s = sub.add_parser("show", help="print the latest and highest months from an existing dataset")
    s.add_argument("--out", type=Path, default=Path("data"))
    args = p.parse_args(argv)

    if args.cmd == "show":
        return _show(args.out)

    def log(msg: str) -> None:
        print(msg, file=sys.stderr)

    fetcher = Fetcher(args.cache, offline=args.offline, log=log if args.verbose else None)
    try:
        doc = build(fetcher, args.out, since=args.since, with_jolts=args.jolts,
                    freeze_days=args.freeze_days, log=log)
    except (BuildError, FetchError) as exc:
        print(f"hn-glut: {exc}", file=sys.stderr)
        return 1
    _print_summary(doc["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
