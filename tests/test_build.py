import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hn_glut.build import BuildError, build
from hn_glut.cli import main
from hn_glut.fetch import ALGOLIA, FIREBASE, FRED_CSV, FetchError, Fetcher

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 25, tzinfo=timezone.utc).timestamp()


def url_to_fixture(url: str) -> Path:
    if url == FRED_CSV:
        return FIXTURES / "fred/jolts.csv"
    if url.startswith(f"{FIREBASE}/user/"):
        return FIXTURES / "firebase" / ("user-" + url.rsplit("/", 1)[1])
    if url.startswith(f"{FIREBASE}/item/"):
        return FIXTURES / "firebase/item" / url.rsplit("/", 1)[1]
    if url.startswith(f"{ALGOLIA}/items/"):
        return FIXTURES / "algolia/items" / (url.rsplit("/", 1)[1] + ".json")
    raise AssertionError(f"unexpected URL {url}")


class FakeHN:
    def __init__(self):
        self.calls = []

    def __call__(self, url: str) -> bytes:
        self.calls.append(url)
        return url_to_fixture(url).read_bytes()


def fetcher(tmp_path, transport=None, **kw):
    return Fetcher(tmp_path / "cache", transport=transport or FakeHN(), delays={}, sleep=lambda _s: None, **kw)


def read_csv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def test_monthly_counts_and_ratios(tmp_path):
    out = tmp_path / "data"
    doc = build(fetcher(tmp_path), out, since="2026-08", with_jolts=True, now=NOW)
    rows = {r["month"]: r for r in read_csv(out / "monthly.csv")}
    assert list(rows) == ["2026-08", "2026-09", "2026-10"]
    # The September hiring thread comes from the stand-in `_whoishiring` account.
    assert rows["2026-09"]["hiring_id"] == "903"
    aug = rows["2026-08"]
    assert (aug["hiring_all"], aug["seeking_all"], aug["ratio_all"]) == ("4", "10", "2.5")
    # Algolia children without text/author are deleted or dead and are not visible.
    assert (aug["hiring_visible"], aug["seeking_visible"], aug["ratio_visible"]) == ("3", "5", "1.67")
    oct_ = rows["2026-10"]
    assert oct_["ratio_all"] == "3.0"
    assert oct_["freelancer_all"] == "3"
    assert oct_["complete"] == "true"
    assert doc["summary"]["latest_complete"]["month"] == "2026-10"
    assert [r["month"] for r in doc["summary"]["highest"]] == ["2026-10", "2026-08", "2026-09"]


def test_skipped_titles_and_dead_threads(tmp_path):
    out = tmp_path / "data"
    build(fetcher(tmp_path), out, since="2026-08", now=NOW)
    skipped = {r["id"]: r["reason"] for r in read_csv(out / "skipped.csv")}
    assert skipped == {"908": "not a monthly thread title", "909": "dead", "910": "deleted"}


def test_in_progress_month_is_not_complete(tmp_path):
    out = tmp_path / "data"
    early = datetime(2026, 10, 10, tzinfo=timezone.utc).timestamp()
    doc = build(fetcher(tmp_path), out, since="2026-08", now=early)
    assert doc["summary"]["in_progress"]["month"] == "2026-10"
    assert doc["summary"]["latest_complete"]["month"] == "2026-09"
    assert "2026-10" not in [r["month"] for r in doc["summary"]["highest"]]


def test_skill_rolling_window(tmp_path):
    out = tmp_path / "data"
    build(fetcher(tmp_path), out, since="2026-08", now=NOW)
    rows = {(r["month"], r["skill"]): r for r in read_csv(out / "skills.csv")}
    rust_aug = rows[("2026-08", "rust")]
    assert (rust_aug["hiring_hits"], rust_aug["seeking_hits"], rust_aug["seekers_per_job_3m"]) == ("1", "1", "")
    rust_oct = rows[("2026-10", "rust")]
    # hiring: Aug 1 + Sep 0 + Oct 1; seeking: Aug 1 + Sep 1 + Oct 2
    assert (rust_oct["hiring_hits_3m"], rust_oct["seeking_hits_3m"], rust_oct["seekers_per_job_3m"]) == ("2", "4", "2.0")
    # "Willing to go anywhere" must not count as Go; "Python/Go" and "Go, Rust" must.
    assert (rows[("2026-08", "go")]["seeking_hits"], rows[("2026-09", "go")]["seeking_hits"], rows[("2026-10", "go")]["seeking_hits"]) == ("1", "1", "1")


def test_jolts(tmp_path):
    out = tmp_path / "data"
    doc = build(fetcher(tmp_path), out, since="2026-08", with_jolts=True, now=NOW)
    assert doc["jolts"] == [{"month": "2026-08", "openings_k": 7079.0, "unemployed_k": 7031.0, "openings_per_unemployed": 1.01}]


def test_cache_then_offline(tmp_path):
    fake = FakeHN()
    build(fetcher(tmp_path, fake), tmp_path / "a", since="2026-08", now=NOW)
    first = len(fake.calls)
    assert first == 2 + 10 + 6  # two accounts + items + Algolia trees for hiring/seeking

    def no_network(url):
        raise AssertionError(f"network used offline: {url}")

    build(fetcher(tmp_path, no_network, offline=True), tmp_path / "b", since="2026-08", now=NOW)
    assert (tmp_path / "a/monthly.csv").read_text() == (tmp_path / "b/monthly.csv").read_text()

    # Online again: the user list and threads younger than --freeze-days are re-fetched, older ones stay cached.
    fake2 = FakeHN()
    build(fetcher(tmp_path, fake2), tmp_path / "c", since="2026-08", now=NOW)
    assert sorted(fake2.calls) == sorted([
        f"{FIREBASE}/user/whoishiring.json", f"{FIREBASE}/user/_whoishiring.json",
        f"{FIREBASE}/item/905.json", f"{FIREBASE}/item/906.json", f"{FIREBASE}/item/907.json",
        f"{ALGOLIA}/items/905", f"{ALGOLIA}/items/906",
    ])


def test_offline_without_cache_fails(tmp_path):
    with pytest.raises(FetchError, match="--offline"):
        build(fetcher(tmp_path, offline=True), tmp_path / "out", since="2026-08", now=NOW)


def test_duplicate_thread_is_an_error(tmp_path):
    fixtures = tmp_path / "fx"
    shutil.copytree(FIXTURES, fixtures)
    item = json.loads((fixtures / "firebase/item/908.json").read_text())
    item["title"] = "Ask HN: Who is hiring? (October 2026)"
    (fixtures / "firebase/item/908.json").write_text(json.dumps(item))

    def transport(url):
        return (fixtures / url_to_fixture(url).relative_to(FIXTURES)).read_bytes()

    with pytest.raises(BuildError, match="two hiring threads for 2026-10"):
        build(fetcher(tmp_path, transport), tmp_path / "out", since="2026-08", now=NOW)


def test_cli_show(tmp_path, capsys):
    out = tmp_path / "data"
    build(fetcher(tmp_path), out, since="2026-08", now=NOW)
    assert main(["show", "--out", str(out)]) == 0
    text = capsys.readouterr().out
    assert "latest complete month  2026-10: 12/4 = 3.0" in text


def test_cli_show_missing_data(tmp_path, capsys):
    assert main(["show", "--out", str(tmp_path / "nope")]) == 1
    assert "run `hn-glut build` first" in capsys.readouterr().err
