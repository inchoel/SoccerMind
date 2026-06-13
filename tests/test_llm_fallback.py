"""폴백 해설 + 스쿼드 검증 가드레일 (불변식 #3, #5)."""

from soccermind.core.models import PlayerStat, ResolvedTeam, ScorerProb
from soccermind.engine.score_matrix import Outcome
from soccermind.llm.base import AugmentInput, validate_against_squads
from soccermind.llm.fallback import FallbackAugmenter, template_explanation


def _input(a_win=0.61, draw=0.18, b_win=0.21):
    return AugmentInput(
        team_a=ResolvedTeam("BRA", "브라질"),
        team_b=ResolvedTeam("KOR", "대한민국"),
        lam_a=1.9, lam_b=1.0,
        outcome=Outcome(a_win=a_win, draw=draw, b_win=b_win),
        scoreline=(2, 1, 0.11),
        top_scorelines=[(2, 1, 0.11)],
        scorers_a=[ScorerProb("Vinicius", 0.5, 0.39)],
        scorers_b=[ScorerProb("Son", 0.4, 0.33)],
    )


def test_template_explanation_mentions_winner_and_score():
    text = template_explanation(_input())
    assert "브라질" in text
    assert "2-1" in text
    assert "Vinicius" in text


def test_template_explanation_draw_case():
    text = template_explanation(_input(a_win=0.3, draw=0.45, b_win=0.25))
    assert "무승부" in text


def test_fallback_augmenter_keeps_scorers():
    inp = _input()
    result = FallbackAugmenter().run(inp)
    assert result.scorers_a == inp.scorers_a
    assert result.scorers_b == inp.scorers_b
    assert result.explanation


def test_fallback_always_available():
    assert FallbackAugmenter().available() is True


# --- 가드레일: validate_against_squads ---

SQUAD = [PlayerStat("Son"), PlayerStat("Lee"), PlayerStat("Kim")]
BASELINE = [ScorerProb("Son", 0.4, 0.33), ScorerProb("Lee", 0.2, 0.18)]


def test_guardrail_accepts_valid_reorder():
    refined = validate_against_squads(["Lee", "Son"], SQUAD, BASELINE)
    assert refined is not None
    assert [s.name for s in refined] == ["Lee", "Son"]
    # baseline 의 확률 유지
    assert refined[1].p_score == 0.33


def test_guardrail_rejects_hallucinated_name():
    # 스쿼드에 없는 'Messi' → None (호출측이 통계 폴백)
    assert validate_against_squads(["Son", "Messi"], SQUAD, BASELINE) is None


def test_guardrail_rejects_empty():
    assert validate_against_squads([], SQUAD, BASELINE) is None


def test_guardrail_squad_member_not_in_baseline_gets_zero():
    # 스쿼드엔 있으나 baseline 밖인 'Kim' → 확률 0 근사로 포함
    refined = validate_against_squads(["Kim", "Son"], SQUAD, BASELINE)
    assert refined is not None
    kim = next(s for s in refined if s.name == "Kim")
    assert kim.p_score == 0.0
