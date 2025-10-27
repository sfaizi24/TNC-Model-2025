"""HTTP utilities with caching and retry support."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(os.getenv("CACHE_DIR", "cache"))
DEFAULT_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class HTTPCache:
    def __init__(self, cache_dir: Path = DEFAULT_CACHE_DIR, ttl: int = 86_400) -> None:
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._cache_path(key)
        if not path.exists():
            return None
        if self.ttl:
            age = time.time() - path.stat().st_mtime
            if age > self.ttl:
                return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            logger.warning("Failed to decode cached JSON for %s", key)
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._cache_path(key)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(value, fh)


async def http_get_json(
    url: str,
    *,
    params: Optional[dict[str, Any]] = None,
    timeout: float = 30.0,
    retries: int = 3,
    backoff: float = 1.5,
    cache: Optional[HTTPCache] = None,
) -> Any:
    """Perform a GET request with retry/backoff and optional caching."""

    cache_key = json.dumps({"url": url, "params": params}, sort_keys=True)
    if cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    async with httpx.AsyncClient(timeout=timeout) as client:
        attempt = 0
        while True:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if cache:
                    cache.set(cache_key, data)
                return data
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                attempt += 1
                if attempt > retries:
                    logger.error("HTTP request failed after %s attempts: %s", attempt, exc)
                    raise
                sleep_for = backoff**attempt
                logger.warning(
                    "Request to %s failed (%s). Retrying in %.1fs (attempt %s/%s)",
                    url,
                    exc,
                    sleep_for,
                    attempt,
                    retries,
                )
                time.sleep(sleep_for)


def sync_http_get_json(url: str, **kwargs: Any) -> Any:
    """Synchronous wrapper around :func:`http_get_json`."""

    import anyio

    return anyio.run(http_get_json, url, **kwargs)
