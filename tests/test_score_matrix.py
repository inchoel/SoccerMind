"""스코어 매트릭스 불변식 검증 (설계 불변식 #1, #2)."""

import math

from soccermind.engine.config import DEFAULT_CONFIG
from soccermind.engine.score_matrix import (
    most_likely_scoreline,
    outcome_probabilities,
    score_matrix,
    top_scorelines,
)


def test_matrix_sums_to_one():
    m = score_matrix(1.8, 1.1)
    total = sum(p for row in m for p in row)
    assert math.isclose(total, 1.0, abs_tol=1e-9)


def test_outcome_probs_sum_to_one():
    m = score_matrix(1.5, 1.5)
    o = outcome_probabilities(m)
    assert math.isclose(o.a_win + o.draw + o.b_win, 1.0, abs_tol=1e-9)


def test_region_mapping_stronger_team_a_wins_more():
    # A 가 훨씬 강하면(λ_A >> λ_B) A승 확률이 B승보다 커야 한다.
    m = score_matrix(2.4, 0.7)
    o = outcome_probabilities(m)
    assert o.a_win > o.b_win
    assert o.a_win > o.draw


def test_region_mapping_symmetry():
    # λ 를 뒤집으면 A승/B승이 대칭으로 뒤집혀야 한다 (영역 매핑 정확성).
    m1 = score_matrix(2.0, 1.0)
    m2 = score_matrix(1.0, 2.0)
    o1 = outcome_probabilities(m1)
    o2 = outcome_probabilities(m2)
    assert math.isclose(o1.a_win, o2.b_win, abs_tol=1e-9)
    assert math.isclose(o1.b_win, o2.a_win, abs_tol=1e-9)
    assert math.isclose(o1.draw, o2.draw, abs_tol=1e-9)


def test_equal_teams_balanced():
    m = score_matrix(1.3, 1.3)
    o = outcome_probabilities(m)
    assert math.isclose(o.a_win, o.b_win, abs_tol=1e-9)


def test_dixon_coles_increases_draw_vs_plain_poisson():
    # rho<0 의 DC 보정은 무승부 확률을 순수 포아송보다 높여야 한다.
    from soccermind.engine.config import ModelConfig

    dc = outcome_probabilities(score_matrix(1.3, 1.3, DEFAULT_CONFIG))
    plain = outcome_probabilities(score_matrix(1.3, 1.3, ModelConfig(rho=0.0)))
    assert dc.draw > plain.draw


def test_most_likely_scoreline_returns_valid_cell():
    m = score_matrix(1.8, 0.9)
    x, y, p = most_likely_scoreline(m)
    assert 0 <= x <= DEFAULT_CONFIG.max_goals
    assert 0 <= y <= DEFAULT_CONFIG.max_goals
    assert p == max(cell for row in m for cell in row)


def test_top_scorelines_sorted_and_sized():
    m = score_matrix(1.6, 1.2)
    top = top_scorelines(m, n=5)
    assert len(top) == 5
    probs = [p for _, _, p in top]
    assert probs == sorted(probs, reverse=True)
