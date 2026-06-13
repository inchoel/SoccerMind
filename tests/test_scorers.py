"""득점자 모델 검증 (기획서 F4)."""

from soccermind.core.models import PlayerStat
from soccermind.engine.scorers import rank_scorers


def _squad():
    return [
        PlayerStat("Striker", intl_goals=30, matches=50, recent_goals=4, recent_matches=5),
        PlayerStat("Midfielder", intl_goals=10, matches=60, recent_goals=1, recent_matches=5),
        PlayerStat("Defender", intl_goals=2, matches=70, recent_goals=0, recent_matches=5),
    ]


def test_top_scorer_is_most_prolific():
    ranked = rank_scorers(1.8, _squad())
    assert ranked[0].name == "Striker"


def test_probabilities_in_unit_interval():
    for s in rank_scorers(1.8, _squad()):
        assert 0.0 <= s.p_score <= 1.0
        assert s.xg >= 0.0


def test_injured_player_excluded():
    squad = _squad()
    squad[0].availability = 0.0  # 주득점원 결장
    names = [s.name for s in rank_scorers(1.8, squad)]
    assert "Striker" not in names


def test_penalty_taker_gets_boost():
    base = PlayerStat("P", intl_goals=10, matches=50, recent_goals=1, recent_matches=5)
    taker = PlayerStat("P", intl_goals=10, matches=50, recent_goals=1, recent_matches=5,
                       is_pen_taker=True)
    s_base = rank_scorers(1.5, [base])[0]
    s_taker = rank_scorers(1.5, [taker])[0]
    assert s_taker.xg > s_base.xg


def test_empty_squad_returns_empty():
    assert rank_scorers(1.5, []) == []


def test_goalkeeper_excluded():
    squad = _squad() + [
        PlayerStat("Keeper", intl_goals=0, matches=80, position="Goalkeeper")
    ]
    names = [s.name for s in rank_scorers(1.8, squad)]
    assert "Keeper" not in names


def test_equal_share_fallback_when_no_goal_stats():
    # 득점 통계가 모두 0이면(무료 티어) 균등 분배로 폴백, 골키퍼는 제외.
    squad = [
        PlayerStat("A", position="Offence"),
        PlayerStat("B", position="Midfield"),
        PlayerStat("GK", position="Goalkeeper"),
    ]
    ranked = rank_scorers(2.0, squad)
    assert {s.name for s in ranked} == {"A", "B"}
    assert abs(ranked[0].xg - ranked[1].xg) < 1e-9  # 균등
