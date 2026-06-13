"""Elo → λ 변환 검증 (설계 불변식 #1)."""

import math

from soccermind.engine.config import DEFAULT_CONFIG
from soccermind.engine.elo import elo_to_lambda, venue_adjustment


def test_equal_ratings_equal_lambda():
    la, lb = elo_to_lambda(1800, 1800)
    assert math.isclose(la, lb, abs_tol=1e-12)


def test_geometric_mean_preserved():
    # √(λ_A·λ_B) = exp(β0) 는 Elo 격차와 무관하게 보존된다.
    anchor = math.exp(DEFAULT_CONFIG.beta0)
    for ra, rb in [(1800, 1800), (2100, 1500), (1600, 1900)]:
        la, lb = elo_to_lambda(ra, rb)
        assert math.isclose(math.sqrt(la * lb), anchor, rel_tol=1e-9)


def test_stronger_team_higher_lambda():
    la, lb = elo_to_lambda(2100, 1600)
    assert la > lb


def test_host_advantage_applied():
    h_a, h_b = venue_adjustment(is_host_a=True, is_host_b=False)
    assert h_a == DEFAULT_CONFIG.host_advantage
    assert h_b == 0.0
    # 동일 레이팅이라도 호스트 보정으로 λ_A > λ_B.
    la, lb = elo_to_lambda(1800, 1800, h_a=h_a, h_b=h_b)
    assert la > lb
