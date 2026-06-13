"""녹아웃 토너먼트 우승확률 검증 (정확한 브래킷 DP)."""

import math

import pytest

from soccermind.engine.tournament import (
    TournamentTeam,
    advance_probability,
    championship_probabilities,
)


def test_advance_probability_symmetry():
    # adv(A,B) + adv(B,A) = 1
    a = advance_probability(2000, 1600)
    b = advance_probability(1600, 2000)
    assert math.isclose(a + b, 1.0, abs_tol=1e-9)


def test_advance_probability_equal_is_half():
    assert math.isclose(advance_probability(1800, 1800), 0.5, abs_tol=1e-9)


def test_advance_stronger_team_favored():
    assert advance_probability(2100, 1500) > 0.5


def test_championship_two_teams():
    teams = [TournamentTeam("A", 2000), TournamentTeam("B", 1600)]
    res = dict(championship_probabilities(teams))
    # 2팀 결승: A 우승확률 = adv(A,B)
    assert math.isclose(res["A"], advance_probability(2000, 1600), abs_tol=1e-9)
    assert math.isclose(res["A"] + res["B"], 1.0, abs_tol=1e-9)


def test_championship_probs_sum_to_one():
    teams = [TournamentTeam(f"T{i}", 1500 + i * 50) for i in range(8)]
    res = championship_probabilities(teams)
    assert math.isclose(sum(p for _, p in res), 1.0, abs_tol=1e-9)


def test_equal_teams_uniform():
    teams = [TournamentTeam(f"T{i}", 1800) for i in range(4)]
    res = dict(championship_probabilities(teams))
    for p in res.values():
        assert math.isclose(p, 0.25, abs_tol=1e-9)


def test_stronger_team_highest_prob_and_sorted():
    teams = [
        TournamentTeam("Weak", 1500),
        TournamentTeam("Strong", 2100),
        TournamentTeam("Mid1", 1750),
        TournamentTeam("Mid2", 1750),
    ]
    res = championship_probabilities(teams)
    # 내림차순 정렬, 최강팀이 1위
    assert res[0][0] == "Strong"
    probs = [p for _, p in res]
    assert probs == sorted(probs, reverse=True)


def test_invalid_team_count_raises():
    with pytest.raises(ValueError):
        championship_probabilities([TournamentTeam(f"T{i}", 1800) for i in range(3)])
    with pytest.raises(ValueError):
        championship_probabilities([TournamentTeam("solo", 1800)])
