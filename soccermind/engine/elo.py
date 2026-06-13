"""Elo 레이팅 → 기대득점(λ) 변환.

설계 불변식 #1: Elo 의 유일한 임무는 λ 산출. 승/무/패는 여기서 계산하지 않는다.
참고: 아키텍처 §4.4, 기획서 §8.
"""

from __future__ import annotations

import math

from .config import DEFAULT_CONFIG, ModelConfig


def venue_adjustment(
    is_host_a: bool, is_host_b: bool, cfg: ModelConfig = DEFAULT_CONFIG
) -> tuple[float, float]:
    """베뉴 보정(H) 반환. 월드컵 기본은 중립(0,0), 개최국만 축소 홈 어드밴티지."""
    h_a = cfg.host_advantage if is_host_a else 0.0
    h_b = cfg.host_advantage if is_host_b else 0.0
    return h_a, h_b


def elo_to_lambda(
    rating_a: float,
    rating_b: float,
    h_a: float = 0.0,
    h_b: float = 0.0,
    cfg: ModelConfig = DEFAULT_CONFIG,
) -> tuple[float, float]:
    """두 팀의 Elo(+베뉴 보정) → (λ_A, λ_B) 기대득점.

    대칭 지수 우위 모델:
        δ   = (R_A + H_A − R_B − H_B) / 400
        λ_A = exp(β0 + β1·δ)
        λ_B = exp(β0 − β1·δ)
    기하평균 총득점 √(λ_A·λ_B) = exp(β0) 는 δ 에 무관하게 보존된다
    (강도 차이는 총득점을 늘리지 않고 두 팀 '사이'로 이동시킨다).
    """
    delta = (rating_a + h_a - rating_b - h_b) / 400.0
    lam_a = math.exp(cfg.beta0 + cfg.beta1 * delta)
    lam_b = math.exp(cfg.beta0 - cfg.beta1 * delta)
    return lam_a, lam_b


def win_expectancy(rating_a: float, rating_b: float, h: float = 0.0) -> float:
    """Elo 표준 기대 결과(0~1). 레이팅 업데이트/참고용이며 승무패 산출에는 쓰지 않는다."""
    dr = rating_a - rating_b + h
    return 1.0 / (10 ** (-dr / 400.0) + 1.0)


def goal_diff_multiplier(goal_diff: int) -> float:
    """득점차 가중 G (World Football Elo): 1골=1.0, 2골=1.5, 3골+=(11+|gd|)/8."""
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11 + gd) / 8.0


def update_rating(
    rating: float, score: float, expected: float, k: float, gd_mult: float = 1.0
) -> float:
    """Elo 업데이트: R_new = R_old + K·G·(W − W_e).

    score(W): 승=1, 무=0.5, 패=0. expected(W_e): win_expectancy 값. k: 대회 가중치.
    """
    return rating + k * gd_mult * (score - expected)
