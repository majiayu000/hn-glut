"""Rate-limited, cached HTTP for the HN Firebase, HN Algolia and FRED endpoints."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from . import __version__

USER_AGENT = f"hn-glut/{__version__} (+https://github.com/majiayu000/hn-glut)"

FIREBASE = "https://hacker-news.firebaseio.com/v0"
ALGOLIA = "https://hn.algolia.com/api/v1"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=JTSJOL,UNEMPLOY"

# Minimum seconds between two requests to the same host.
DEFAULT_DELAYS = {
    "hacker-news.firebaseio.com": 0.2,
    "hn.algolia.com": 1.0,
    "fred.stlouisfed.org": 1.0,
}

Transport = Callable[[str], bytes]


class FetchError(RuntimeError):
    pass


def urllib_transport(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


class Fetcher:
    """Fetches URLs once, stores the raw body under cache_dir, and spaces requests per host.

    `fresh=True` ignores an existing cache entry (used for data that can still change).
    In offline mode a missing cache entry is an error, never a silent gap.
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        offline: bool = False,
        transport: Transport = urllib_transport,
        delays: dict[str, float] | None = None,
        retries: int = 3,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] | None = None,
    ):
        self.cache_dir = Path(cache_dir)
        self.offline = offline
        self.transport = transport
        self.delays = DEFAULT_DELAYS if delays is None else delays
        self.retries = retries
        self.sleep = sleep
        self.log = log or (lambda _msg: None)
        self._last: dict[str, float] = {}
        self.requests = 0

    def has(self, cache_key: str) -> bool:
        return (self.cache_dir / cache_key).exists()

    def get(self, url: str, cache_key: str, *, fresh: bool = False) -> bytes:
        path = self.cache_dir / cache_key
        if path.exists() and (self.offline or not fresh):
            return path.read_bytes()
        if self.offline:
            raise FetchError(f"--offline: no cached copy of {url} at {path}")
        body = self._request(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(body)
        tmp.replace(path)
        return body

    def get_json(self, url: str, cache_key: str, *, fresh: bool = False):
        body = self.get(url, cache_key, fresh=fresh)
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise FetchError(f"{url}: response is not JSON ({exc})") from exc

    def _request(self, url: str) -> bytes:
        host = urlparse(url).hostname or ""
        delay = self.delays.get(host, 1.0)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            wait = self._last.get(host, 0.0) + delay - time.monotonic()
            if wait > 0:
                self.sleep(wait)
            self._last[host] = time.monotonic()
            self.requests += 1
            try:
                self.log(f"GET {url}")
                return self.transport(url)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                last_error = exc
                if attempt < self.retries:
                    self.sleep(2 ** (attempt + 1))
        raise FetchError(f"{url}: failed after {self.retries + 1} attempts: {last_error}")
