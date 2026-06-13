"""Elo replay 검증 — 경기 전 레이팅 재구성 (World Football Elo)."""

import math

from soccermind.engine.elo import goal_diff_multiplier, update_rating
from soccermind.engine.rating_history import MatchResult, replay


def test_goal_diff_multiplier():
    assert goal_diff_multiplier(0) == 1.0
    assert goal_diff_multiplier(1) == 1.0
    assert goal_diff_multiplier(2) == 1.5
    assert math.isclose(goal_diff_multiplier(3), 14 / 8)
    assert math.isclose(goal_diff_multiplier(4), 15 / 8)


def test_update_rating_winner_gains():
    # 동급(we=0.5) 승리 시 +K·G·0.5
    new = update_rating(1500, score=1.0, expected=0.5, k=60, gd_mult=1.0)
    assert new == 1530.0


def test_replay_records_pregame_ratings():
    results = [MatchResult("A", "B", 1, 0, k_weight=60)]
    ratings, matches = replay(results)
    # 첫 경기는 기본 레이팅으로 기록
    assert matches[0].rating_a == 1500.0
    assert matches[0].rating_b == 1500.0
    assert matches[0].result_index == 0  # A승


def test_replay_zero_sum_update():
    ratings, _ = replay([MatchResult("A", "B", 1, 0, k_weight=60)])
    # 제로섬: A 상승분 == B 하락분
    assert math.isclose(ratings["A"] - 1500.0, 1500.0 - ratings["B"])
    assert ratings["A"] == 1530.0
    assert ratings["B"] == 1470.0


def test_replay_winner_rating_climbs_over_time():
    # A가 B를 계속 이기면 A 레이팅이 단조 상승
    results = [MatchResult("A", "B", 2, 0) for _ in range(5)]
    ratings, matches = replay(results)
    pregame_a = [m.rating_a for m in matches]
    assert pregame_a == sorted(pregame_a)  # 비감소
    assert ratings["A"] > 1500.0 > ratings["B"]


def test_replay_draw_minimal_change_between_equals():
    ratings, _ = replay([MatchResult("A", "B", 1, 1, k_weight=60)])
    # 동급 무승부 → 변화 없음 (we=0.5, w=0.5)
    assert math.isclose(ratings["A"], 1500.0)
    assert math.isclose(ratings["B"], 1500.0)
