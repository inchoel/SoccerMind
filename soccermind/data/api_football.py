"""API-Football (api-sports.io) — WC 심층 선수 득점 통계 (선택, 무료 100/일).

football-data 는 스쿼드 이름만 주지만, API-Football 은 선수별 득점·출전·페널티를 줘
득점자 예측 품질을 높인다. 파싱(parse_players, 순수)과 fetch(I/O) 분리.
설계 불변식 #5: 키 없으면 available()=False 로 자동 스킵.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import Callable
from typing import Any

from ..core.models import PartialTeamData, PlayerStat, ResolvedTeam
from .base import DataProvider
from .cache import DiskCache

BASE_URL = "https://v3.football.api-sports.io"
_TTL = 24 * 3600
# 예측 수행 시점의 연도를 시즌으로 사용 (최신 정보 반영)
DEFAULT_SEASON = datetime.date.today().year


def _int(v: Any) -> int:
    return int(v) if isinstance(v, (int, float)) else 0


def parse_players(data: dict[str, Any]) -> list[PlayerStat]:
    """players 응답 JSON → PlayerStat 목록 (이름·득점·출전·포지션·PK)."""
    out: list[PlayerStat] = []
    for item in data.get("response", []) or []:
        player = item.get("player") or {}
        name = player.get("name")
        if not name:
            continue
        stats = (item.get("statistics") or [{}])[0] or {}
        games = stats.get("games") or {}
        goals = stats.get("goals") or {}
        penalty = stats.get("penalty") or {}
        appearances = _int(games.get("appearences"))  # API-Football 철자
        total_goals = _int(goals.get("total"))
        out.append(
            PlayerStat(
                name=name,
                intl_goals=total_goals,
                matches=appearances,
                recent_goals=total_goals,
                recent_matches=appearances,
                position=games.get("position") or "",
                is_pen_taker=_int(penalty.get("scored")) > 0,
            )
        )
    return out


def _default_fetch_json(url: str, key: str) -> dict[str, Any]:
    import httpx

    headers = {"x-apisports-key": key, "User-Agent": "SoccerMind/0.1"}
    resp = httpx.get(url, headers=headers, timeout=15.0)
    resp.raise_for_status()
    return resp.json()


class ApiFootballProvider(DataProvider):
    name = "api_football"

    def __init__(
        self,
        key: str | None = None,
        season: int = DEFAULT_SEASON,
        fetch_json: Callable[[str, str], dict[str, Any]] = _default_fetch_json,
        cache: DiskCache | None = None,
    ) -> None:
        self._key = key if key is not None else os.environ.get("API_FOOTBALL_KEY", "")
        self._season = season
        self._fetch_json = fetch_json
        self._cache = cache or DiskCache()

    def available(self) -> bool:
        return bool(self._key)

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        if not self.available() or team.api_football_id is None:
            return PartialTeamData(source=self.name)
        url = f"{BASE_URL}/players?team={team.api_football_id}&season={self._season}"
        try:
            data = self._cache.get_or_fetch(url, _TTL, lambda: self._fetch_json(url, self._key))
        except Exception:
            return PartialTeamData(source=self.name)
        return PartialTeamData(source=self.name, squad=parse_players(data))
