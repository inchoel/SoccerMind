"""football-data.org v4 — 백본 데이터 (스쿼드). 무료 자가발급 키 (X-Auth-Token).

파싱(parse_squad, 순수)과 fetch(I/O) 분리. 무료 티어는 per-player 득점 통계가
빈약하므로 MVP 는 스쿼드 명단 위주(득점 통계는 0, scorers 가 균등 폴백).
설계 불변식 #5: 키 없으면 available()=False 로 자동 스킵.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from ..core.models import PartialTeamData, PlayerStat, ResolvedTeam
from .base import DataProvider
from .cache import DiskCache

BASE_URL = "https://api.football-data.org/v4"
_TTL = 24 * 3600  # 스쿼드는 24h


def parse_squad(team_json: dict[str, Any]) -> list[PlayerStat]:
    """team 리소스 JSON → PlayerStat 목록 (이름·포지션)."""
    squad: list[PlayerStat] = []
    for person in team_json.get("squad", []) or []:
        name = person.get("name")
        if not name:
            continue
        squad.append(PlayerStat(name=name, position=person.get("position") or ""))
    return squad


def _default_fetch_json(url: str, token: str) -> dict[str, Any]:
    import httpx

    headers = {"X-Auth-Token": token, "User-Agent": "SoccerMind/0.1"}
    resp = httpx.get(url, headers=headers, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


class FootballDataProvider(DataProvider):
    name = "football_data"

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

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        if not self.available() or team.fd_id is None:
            return PartialTeamData(source=self.name)
        url = f"{BASE_URL}/teams/{team.fd_id}"
        try:
            data = self._cache.get_or_fetch(
                url, _TTL, lambda: self._fetch_json(url, self._token)
            )
        except Exception:
            return PartialTeamData(source=self.name)
        return PartialTeamData(source=self.name, squad=parse_squad(data))
