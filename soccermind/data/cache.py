"""TTL 파일 캐시 — 무료 API 한도(100/일, 10/분) 보호 (아키텍처 §4.3).

clock 주입으로 TTL 만료를 테스트 가능. loader 실패 시 만료 캐시로 폴백.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(self, root: str | Path = "data_cache", clock: Callable[[], float] = time.time):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str, ttl_sec: float) -> Any | None:
        """캐시 적중이고 TTL 내면 payload, 아니면 None."""
        path = self._path(key)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if self._clock() - entry.get("fetched_at", 0) > ttl_sec:
            return None
        return entry.get("payload")

    def set(self, key: str, payload: Any) -> None:
        entry = {"fetched_at": self._clock(), "payload": payload}
        self._path(key).write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")

    def _read_stale(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("payload")
        except (json.JSONDecodeError, OSError):
            return None

    def get_or_fetch(self, key: str, ttl_sec: float, loader: Callable[[], Any]) -> Any:
        """TTL 내 캐시 반환, 없으면 loader() 호출·저장. loader 실패 시 만료 캐시로 폴백."""
        cached = self.get(key, ttl_sec)
        if cached is not None:
            return cached
        try:
            payload = loader()
        except Exception:
            stale = self._read_stale(key)
            if stale is not None:
                return stale
            raise
        self.set(key, payload)
        return payload
