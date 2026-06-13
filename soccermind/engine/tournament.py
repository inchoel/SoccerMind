"""녹아웃 토너먼트 우승 확률 — 정확한 브래킷 DP (몬테카를로 미사용).

진출 확률은 스코어 매트릭스에서 산출(불변식 #1). 무승부는 승부차기 50/50 으로 처리.
브래킷 DP 는 각 라운드에서 가능한 상대를 도달확률로 가중해 정확히 합산 → 결정적.
참고: 아키텍처 §10(향후).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import DEFAULT_CONFIG, ModelConfig
from .elo import elo_to_lambda
from .score_matrix import outcome_probabilities, score_matrix


@dataclass(frozen=True)
class TournamentTeam:
    name: str
    rating: float


def advance_probability(
    rating_a: float,
    rating_b: float,
    cfg: ModelConfig = DEFAULT_CONFIG,
    h_a: float = 0.0,
    h_b: float = 0.0,
) -> float:
    """녹아웃에서 A가 B를 꺾고 진출할 확률 = P(A승) + 0.5·P(무) (승부차기 동전던지기)."""
    lam_a, lam_b = elo_to_lambda(rating_a, rating_b, h_a, h_b, cfg)
    o = outcome_probabilities(score_matrix(lam_a, lam_b, cfg))
    return o.a_win + 0.5 * o.draw


def _is_power_of_two(n: int) -> bool:
    return n >= 2 and (n & (n - 1)) == 0


def championship_probabilities(
    teams: list[TournamentTeam], cfg: ModelConfig = DEFAULT_CONFIG
) -> list[tuple[str, float]]:
    """브래킷 시드 순서 팀 목록(2의 거듭제곱) → 우승 확률 내림차순 [(이름, 확률)].

    DP: P[i] = 팀 i 가 현재 라운드에 도달할 확률. 매 라운드 블록이 2배가 되며,
    블록의 반대편 절반에 있는 가능한 상대 j 를 P[j]·advance(i,j) 로 가중 합산.
    """
    n = len(teams)
    if not _is_power_of_two(n):
        raise ValueError(f"팀 수는 2의 거듭제곱이어야 합니다 (받음: {n})")

    rounds = int(math.log2(n))
    # 진출확률 캐시 (대칭쌍 중복 계산 방지)
    adv: dict[tuple[int, int], float] = {}

    def adv_ij(i: int, j: int) -> float:
        key = (i, j)
        if key not in adv:
            p = advance_probability(teams[i].rating, teams[j].rating, cfg)
            adv[key] = p
            adv[(j, i)] = 1.0 - p
        return adv[key]

    prob = [1.0] * n
    block = 1
    for _ in range(rounds):
        block *= 2
        half = block // 2
        new = [0.0] * n
        for start in range(0, n, block):
            left = range(start, start + half)
            right = range(start + half, start + block)
            for i in left:
                new[i] = prob[i] * sum(prob[j] * adv_ij(i, j) for j in right)
            for i in right:
                new[i] = prob[i] * sum(prob[j] * adv_ij(i, j) for j in left)
        prob = new

    return sorted(
        ((teams[i].name, prob[i]) for i in range(n)), key=lambda x: x[1], reverse=True
    )
