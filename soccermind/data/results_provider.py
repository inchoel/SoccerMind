"""football-data.org 종료 경기 결과 → 시간순 MatchResult (replay/보정 입력).

파싱(parse_finished_matches, 순수)과 fetch(I/O) 분리. 토너먼트 경기는 중립으로 처리.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from ..engine.rating_history import K_WORLD_CUP, MatchResult
from .cache import DiskCache
from .football_data import BASE_URL, _default_fetch_json

_TTL = 24 * 3600


def parse_finished_matches(
    data: dict[str, Any], k_weight: float = K_WORLD_CUP
) -> list[MatchResult]:
    """competition matches JSON → 종료 경기만 시간순 MatchResult.

    중립 경기로 가정(토너먼트). status=FINISHED, fullTime 스코어가 있어야 포함.
    """
    rows: list[MatchResult] = []
    for m in data.get("matches", []) or []:
        if m.get("status") != "FINISHED":
            continue
        ft = (m.get("score") or {}).get("fullTime") or {}
        ha, aw = ft.get("home"), ft.get("away")
        if ha is None or aw is None:
            continue
        home = (m.get("homeTeam") or {}).get("name")
        away = (m.get("awayTeam") or {}).get("name")
        if not home or not away:
            continue
        rows.append(
            MatchResult(team_a=home, team_b=away, goals_a=int(ha), goals_b=int(aw),
                        k_weight=k_weight, date=m.get("utcDate"))
        )
    rows.sort(key=lambda r: r.date or "")
    return rows


class ResultsProvider:
    """football-data 대회의 종료 경기 결과를 시간순으로 가져온다."""

    name = "football_data_results"

    def __init__(
        self,
        token: str | None = None,
        fetch_json: Callable[[str, str], dict[str, Any]] = _default_fetch_json,
        cache: DiskCache | None = None,
    ) -> None:
        self._token = token if token is not None else os.environ.get("FOOTBALL_DATA_TOKEN", "")
        self._fetch_json = fetch_json
        self._cache = cache or DiskCache()

    def available(self) -> bool:
        return bool(self._token)

    def fetch_competition(
        self, code: str, k_weight: float = K_WORLD_CUP
    ) -> list[MatchResult]:
        """대회 코드(예: 'WC', 'EC')의 종료 경기 결과 (시간순)."""
        if not self.available():
            return []
        url = f"{BASE_URL}/competitions/{code}/matches?status=FINISHED"
        try:
            data = self._cache.get_or_fetch(url, _TTL, lambda: self._fetch_json(url, self._token))
        except Exception:
            return []
        return parse_finished_matches(data, k_weight=k_weight)
