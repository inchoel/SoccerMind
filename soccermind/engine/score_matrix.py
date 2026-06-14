"""스코어 매트릭스 — 유일한 진실의 원천 (설계 불변식 #1, #2).

M[x][y] = P(A가 x골, B가 y골). Dixon-Coles 보정 독립 포아송.
승/무/패와 스코어라인은 '반드시' 이 매트릭스에서 읽는다 — Elo 등에서 직접 계산 금지.
순수 Python (numpy 미사용) 으로 의존성·테스트 마찰 제거.
참고: 아키텍처 §4.4.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import DEFAULT_CONFIG, ModelConfig


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def _dixon_coles_tau(x: int, y: int, lam_a: float, lam_b: float, rho: float) -> float:
    """저점수 4개 셀(0-0, 1-0, 0-1, 1-1)에만 적용되는 보정항."""
    if x == 0 and y == 0:
        return 1.0 - lam_a * lam_b * rho
    if x == 1 and y == 0:
        return 1.0 + lam_b * rho
    if x == 0 and y == 1:
        return 1.0 + lam_a * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(
    lam_a: float, lam_b: float, cfg: ModelConfig = DEFAULT_CONFIG
) -> list[list[float]]:
    """정규화된 스코어 확률 매트릭스 M[x][y] 반환 (행=A골, 열=B골).

    τ 적용 후 합이 1에서 약간 벗어나므로 재정규화한다.
    """
    n = cfg.max_goals
    m = [[0.0] * (n + 1) for _ in range(n + 1)]
    total = 0.0
    for x in range(n + 1):
        px = _poisson_pmf(x, lam_a)
        for y in range(n + 1):
            val = px * _poisson_pmf(y, lam_b) * _dixon_coles_tau(x, y, lam_a, lam_b, cfg.rho)
            m[x][y] = val
            total += val
    # 재정규화 (불변식: Σ M = 1)
    for x in range(n + 1):
        for y in range(n + 1):
            m[x][y] /= total
    return m


@dataclass(frozen=True)
class Outcome:
    a_win: float
    draw: float
    b_win: float


def outcome_probabilities(matrix: list[list[float]]) -> Outcome:
    """매트릭스에서 승/무/패 확률.

    M[x][y]=P(A가 x골, B가 y골) 이므로:
        A승 = x>y (하삼각, 대각선 아래), 무 = x=y (대각선), B승 = x<y (상삼각).
    """
    a_win = draw = b_win = 0.0
    for x, row in enumerate(matrix):
        for y, p in enumerate(row):
            if x > y:
                a_win += p
            elif x == y:
                draw += p
            else:
                b_win += p
    return Outcome(a_win=a_win, draw=draw, b_win=b_win)


def most_likely_scoreline(matrix: list[list[float]]) -> tuple[int, int, float]:
    """최빈 스코어라인 (A골, B골, 확률) — 매트릭스의 argmax 셀."""
    best_x = best_y = 0
    best_p = -1.0
    for x, row in enumerate(matrix):
        for y, p in enumerate(row):
            if p > best_p:
                best_p, best_x, best_y = p, x, y
    return best_x, best_y, best_p


def most_likely_scoreline_for(
    matrix: list[list[float]], region: str
) -> tuple[int, int, float]:
    """예측 결과(region)와 '일치하는' 가장 가능성 높은 스코어.

    region: 'a'(A승, x>y) / 'draw'(무, x=y) / 'b'(B승, x<y).
    승리 예상인데 1-1(무) 이 표시되는 모순을 막기 위해, 헤드라인 스코어를
    예측된 결과 영역 안에서 고른다.
    """
    best_x = best_y = 0
    best_p = -1.0
    for x, row in enumerate(matrix):
        for y, p in enumerate(row):
            in_region = (
                (region == "a" and x > y)
                or (region == "draw" and x == y)
                or (region == "b" and x < y)
            )
            if in_region and p > best_p:
                best_p, best_x, best_y = p, x, y
    return best_x, best_y, best_p


def top_scorelines(matrix: list[list[float]], n: int = 5) -> list[tuple[int, int, float]]:
    """확률 상위 N개 스코어라인 [(A골, B골, 확률), ...]."""
    cells = [
        (x, y, p) for x, row in enumerate(matrix) for y, p in enumerate(row)
    ]
    cells.sort(key=lambda c: c[2], reverse=True)
    return cells[:n]
