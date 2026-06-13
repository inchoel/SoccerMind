"""국가명 정규화 (설계 불변식 #4, 기획서 F1).

한/영, 약칭·정식명, 별칭 → 표준키(ISO alpha-3). 실패 시 퍼지 매칭 후보 제안.
의존성 없는 stdlib(difflib)만 사용.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from .aliases import TEAMS, TeamAlias
from .models import Ambiguous, ResolvedTeam


def _normalize(s: str) -> str:
    """비교용 정규화: 소문자, 공백/구두점 정리."""
    s = s.strip().lower()
    for ch in ".-_'":
        s = s.replace(ch, "")
    return " ".join(s.split())


def _to_resolved(t: TeamAlias) -> ResolvedTeam:
    return ResolvedTeam(
        key=t.key,
        display=t.display,
        elo_name=t.elo_name,
        fd_id=t.fd_id,
        api_football_id=t.api_football_id,
        wikipedia=t.wikipedia,
    )


class NameResolver:
    """별칭 역인덱스 + 퍼지 매칭으로 국가명을 표준키로 정규화."""

    def __init__(self, teams: tuple[TeamAlias, ...] = TEAMS) -> None:
        self._teams = teams
        self._index: dict[str, TeamAlias] = {}
        for t in teams:
            keys = {t.key, t.display, *t.aliases}
            for k in keys:
                self._index[_normalize(k)] = t

    def resolve(self, raw: str, fuzzy_cutoff: float = 0.82) -> ResolvedTeam | Ambiguous:
        """raw 국가명 → ResolvedTeam, 모호하면 Ambiguous(후보)."""
        if not raw or not raw.strip():
            return Ambiguous(query=raw, candidates=[])

        norm = _normalize(raw)
        # 1) 정확 일치
        if norm in self._index:
            return _to_resolved(self._index[norm])

        # 2) 퍼지 매칭 — 별칭 키에 대해 유사도 점수
        scored: list[tuple[float, TeamAlias]] = []
        seen: set[str] = set()
        for alias_norm, team in self._index.items():
            ratio = SequenceMatcher(None, norm, alias_norm).ratio()
            if team.key not in seen or ratio > 0:
                scored.append((ratio, team))
        # 팀별 최고 점수만 유지
        best_by_key: dict[str, tuple[float, TeamAlias]] = {}
        for ratio, team in scored:
            cur = best_by_key.get(team.key)
            if cur is None or ratio > cur[0]:
                best_by_key[team.key] = (ratio, team)
        ranked = sorted(best_by_key.values(), key=lambda x: x[0], reverse=True)

        if ranked and ranked[0][0] >= fuzzy_cutoff:
            return _to_resolved(ranked[0][1])

        # 3) 모호 — 상위 3개 후보 제안
        candidates = [_to_resolved(t) for _, t in ranked[:3]]
        return Ambiguous(query=raw, candidates=candidates)

    def all_teams(self) -> list[ResolvedTeam]:
        """지원 국가 전체 (UI 자동완성용)."""
        return [_to_resolved(t) for t in self._teams]
