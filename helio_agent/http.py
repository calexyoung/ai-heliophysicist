"""Content-addressed HTTP cache (pattern from helio-agent's core/cache.py).

Every direct HTTP GET the tools make goes through cached_get(). Responses are
cached under sha256(method + url + sorted public params); credential-bearing
params are excluded from the key AND never written to disk. Non-2xx responses
can be recorded too (allow_error) so fallback chains replay identically.

Modes (HELIO_CACHE_MODE env var):
    readwrite  (default) use cache, fetch+store on miss
    readonly   use cache only; a miss raises CacheMiss (replay mode)
    bypass     always fetch, never store

Scope note: this covers requests made directly by our tools (CDAWeb REST,
DONKI, NOAA SWPC, Helioviewer, HelioData, arXiv, Kyoto, GFZ). Library-managed
transfers (cdasws get_data, sunpy Fido, sscws, pyspedas) keep their own
download caches under workspace/data and are replayed at the file level via
artifact checksums instead.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path

import requests

from helio_agent.workspace import CACHE_DIR
SECRET_PARAMS = {"api_key", "apikey", "token", "key", "mailto", "authorization"}
_UA = {"User-Agent": "helio-agent/0.1 (AI Heliophysicist)"}

# Cache keys touched during the current tool call (collected into the audit
# manifest by registry.run_tool).
_local = threading.local()


class CacheMiss(RuntimeError):
    """readonly mode: the request was never recorded."""


@dataclass
class CachedResponse:
    status_code: int
    content: bytes
    url: str
    cache_key: str
    from_cache: bool

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.content)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def raise_for_status(self) -> None:
        if not self.ok:
            raise requests.HTTPError(
                f"{self.status_code} error for {self.url} (cached={self.from_cache})")


def reset_touched() -> None:
    _local.keys = []


def touched_keys() -> list[str]:
    return list(getattr(_local, "keys", []))


def cache_key(url: str, params: dict | None = None, method: str = "GET") -> str:
    public = {k: str(v) for k, v in sorted((params or {}).items())
              if k.lower() not in SECRET_PARAMS}
    blob = json.dumps([method.upper(), url, public], separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _path(key: str) -> Path:
    return CACHE_DIR / key[:2] / f"{key}.json"


def cache_mode() -> str:
    mode = os.environ.get("HELIO_CACHE_MODE", "readwrite")
    if mode not in ("readwrite", "readonly", "bypass"):
        raise ValueError(f"bad HELIO_CACHE_MODE {mode!r}")
    return mode


def cached_get(url: str, params: dict | None = None, headers: dict | None = None,
               timeout: int = 90, allow_error: bool = False,
               ttl_seconds: float | None = None) -> CachedResponse:
    """GET with content-addressed caching. See module docstring for modes.

    allow_error: cache non-2xx responses as well (for fallback chains);
    otherwise errors are raised and never cached.
    ttl_seconds: treat a cached entry older than this as stale and refetch
    (use for real-time/nowcast feeds; archival endpoints omit it). Replay
    (readonly mode) ignores TTL — it always uses whatever was recorded.
    """
    import time as _time
    key = cache_key(url, params)
    keys = getattr(_local, "keys", None)
    if keys is not None:
        keys.append(key)
    mode = cache_mode()
    fpath = _path(key)

    if mode != "bypass" and fpath.exists():
        entry = json.loads(fpath.read_text())
        fresh = (ttl_seconds is None or mode == "readonly"
                 or _time.time() - entry.get("fetched_at", 0) <= ttl_seconds)
        if fresh:
            return CachedResponse(status_code=entry["status"],
                                  content=base64.b64decode(entry["body_b64"]),
                                  url=entry["url"], cache_key=key, from_cache=True)
    if mode == "readonly":
        raise CacheMiss(f"no cached response for {url} (key {key[:12]}...)")

    r = requests.get(url, params=params, headers={**_UA, **(headers or {})},
                     timeout=timeout)
    if not (200 <= r.status_code < 300) and not allow_error:
        r.raise_for_status()
    if mode == "readwrite":
        fpath.parent.mkdir(parents=True, exist_ok=True)
        redacted_url = r.url
        for s in SECRET_PARAMS:
            if params and s in {k.lower() for k in params}:
                redacted_url = url  # store the pre-substitution URL instead
                break
        import time as _time
        fpath.write_text(json.dumps({
            "status": r.status_code, "url": redacted_url,
            "fetched_at": _time.time(),
            "body_b64": base64.b64encode(r.content).decode(),
        }))
    return CachedResponse(status_code=r.status_code, content=r.content,
                          url=r.url, cache_key=key, from_cache=False)
