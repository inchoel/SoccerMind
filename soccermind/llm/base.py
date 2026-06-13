"""Augmenter 인터페이스 + 가드레일 헬퍼 (설계 불변식 #3).

LLM 은 득점자 재랭킹과 해설만 담당. 확률·스코어는 입력으로 받되 출력에 영향 없음.
validate_against_squads: 스쿼드에 없는 이름이 나오면 통계 랭킹으로 폴백시키는 가드레일.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..core.models import PlayerStat, ResolvedTeam, ScorerProb
from ..engine.score_matrix import Outcome


@dataclass
class AugmentInput:
    team_a: ResolvedTeam
    team_b: ResolvedTeam
    lam_a: float
    lam_b: float
    outcome: Outcome
    scoreline: tuple[int, int, float]
    top_scorelines: list[tuple[int, int, float]]
    scorers_a: list[ScorerProb]
    scorers_b: list[ScorerProb]
    squad_a: list[PlayerStat] = field(default_factory=list)
    squad_b: list[PlayerStat] = field(default_factory=list)
    context: dict = field(default_factory=dict)


@dataclass
class AugmentResult:
    scorers_a: list[ScorerProb]
    scorers_b: list[ScorerProb]
    explanation: str


@runtime_checkable
class Augmenter(Protocol):
    def available(self) -> bool: ...
    def run(self, inp: AugmentInput) -> AugmentResult: ...


def validate_against_squads(
    refined: list[str],
    squad: list[PlayerStat],
    baseline: list[ScorerProb],
) -> list[ScorerProb] | None:
    """LLM 이 재랭킹한 이름 목록을 스쿼드로 검증.

    하나라도 스쿼드에 없으면 None 반환(→ 호출측이 baseline 통계 랭킹으로 폴백).
    모두 유효하면 baseline 의 xG/확률을 유지한 채 LLM 순서로 재정렬.
    """
    squad_names = {p.name for p in squad}
    if not refined:
        return None
    if any(name not in squad_names for name in refined):
        return None
    by_name = {s.name: s for s in baseline}
    reordered: list[ScorerProb] = []
    for name in refined:
        if name in by_name:
            reordered.append(by_name[name])
        else:
            # 스쿼드엔 있으나 baseline 상위 N 밖 → 통계 확률 0 근사로 추가
            reordered.append(ScorerProb(name=name, xg=0.0, p_score=0.0))
    return reordered
