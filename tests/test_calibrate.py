"""보정 러너 검증 — 합성 결과로 replay→fit (네트워크 없음)."""

import itertools

import pytest

from soccermind.calibrate import calibrate_from_results
from soccermind.engine.rating_history import MatchResult


def _decisive_results(rounds: int = 12) -> list[MatchResult]:
    """4팀, 강도 A>B>C>D. 강팀(작은 인덱스)이 항상 2-0 승."""
    teams = ["A", "B", "C", "D"]
    out: list[MatchResult] = []
    for _ in range(rounds):
        for hi, lo in itertools.combinations(range(4), 2):  # hi<lo → hi 가 강함
            out.append(MatchResult(teams[hi], teams[lo], 2, 0))
    return out


def test_calibrate_runs_and_reports():
    res = calibrate_from_results(_decisive_results())
    assert res.n_matches == len(_decisive_results())
    # 피팅 상수는 그리드 범위 내
    assert 0.20 <= res.fitted.beta1 <= 0.70
    # 리포트 유효
    assert 0.0 <= res.report_after.rps <= 1.0
    assert 0.0 <= res.report_after.accuracy <= 1.0


def test_calibrate_improves_rps():
    res = calibrate_from_results(_decisive_results())
    # 결정적 데이터 → 보정 후 RPS 가 개선(또는 동일)
    assert res.report_after.rps <= res.report_before.rps + 1e-9


def test_calibrate_decisive_data_prefers_higher_confidence():
    res = calibrate_from_results(_decisive_results())
    # 명확한 데이터는 더 높은 β1(확신)을 선호
    assert res.fitted.beta1 >= 0.40
    # 정확도 양호 (레이팅이 분리된 후 강팀 승 예측)
    assert res.report_after.accuracy >= 0.6


def test_calibrate_too_few_matches_raises():
    with pytest.raises(ValueError):
        calibrate_from_results([MatchResult("A", "B", 1, 0)])
