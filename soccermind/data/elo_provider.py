"""eloratings.net World Elo 레이팅 (키 불필요).

파싱(parse_elo_tsv, 순수)과 fetch(I/O) 분리 → 한도/네트워크 없이 테스트.
TSV 형식 드리프트에 견디도록 관용적 파싱: 각 행에서 팀명(비숫자)과
레이팅(1000~2500 정수)을 탐지.
"""

from __future__ import annotations

from collections.abc import Callable

from ..core.models import PartialTeamData, ResolvedTeam
from .base import DataProvider
from .cache import DiskCache

WORLD_TSV_URL = "https://www.eloratings.net/World.tsv"
_TTL = 24 * 3600  # 24h (느린 데이터)


def _looks_like_rating(s: str) -> bool:
    return s.isdigit() and 1000 <= int(s) <= 2500


def parse_elo_tsv(text: str) -> dict[str, float]:
    """World.tsv → {elo_name: rating}. 관용적 파싱."""
    ratings: dict[str, float] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        cols = [c.strip() for c in line.split("\t")]
        name: str | None = None
        rating: float | None = None
        for c in cols:
            if not c:
                continue
            if rating is None and _looks_like_rating(c):
                rating = float(c)
            elif name is None and not c.isdigit():
                name = c
        if name and rating is not None:
            ratings[name] = rating
    return ratings


def _default_fetch_text(url: str) -> str:
    import httpx

    headers = {"User-Agent": "SoccerMind/0.1 (open-source predictor)"}
    resp = httpx.get(url, headers=headers, timeout=15.0)
    resp.raise_for_status()
    return resp.text


class EloProvider(DataProvider):
    """팀 강도(Elo) 제공. 키 불필요이므로 항상 available."""

    name = "elo"

    def __init__(
        self,
        fetch_text: Callable[[str], str] = _default_fetch_text,
        cache: DiskCache | None = None,
    ) -> None:
        self._fetch_text = fetch_text
        self._cache = cache or DiskCache()

    def available(self) -> bool:
        return True

    def _ratings(self) -> dict[str, float]:
        text = self._cache.get_or_fetch(
            WORLD_TSV_URL, _TTL, lambda: self._fetch_text(WORLD_TSV_URL)
        )
        return parse_elo_tsv(text)

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        ratings = self._ratings()
        elo = ratings.get(team.elo_name) if team.elo_name else None
        return PartialTeamData(source=self.name, elo=elo)
