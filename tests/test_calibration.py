"""모델 보정·백테스트 검증 — 합성 과거경기."""

from dataclasses import replace

from soccermind.engine.calibration import (
    HistoricalMatch,
    backtest,
    evaluate,
    fit,
    predicted_probs,
)
from soccermind.engine.config import DEFAULT_CONFIG


# 합성: 강팀(높은 Elo)이 이기고, 동급은 무승부
MATCHES = [
    HistoricalMatch(2000, 1500, 2, 0),
    HistoricalMatch(2050, 1450, 3, 0),
    HistoricalMatch(1500, 2000, 0, 2),
    HistoricalMatch(1450, 2050, 0, 3),
    HistoricalMatch(1800, 1800, 1, 1),
    HistoricalMatch(1750, 1750, 0, 0),
    HistoricalMatch(1900, 1600, 1, 0),
    HistoricalMatch(1600, 1900, 0, 1),
]


def test_result_index():
    assert HistoricalMatch(1, 1, 2, 0).result_index == 0
    assert HistoricalMatch(1, 1, 1, 1).result_index == 1
    assert HistoricalMatch(1, 1, 0, 2).result_index == 2


def test_predicted_probs_sum_to_one():
    p = predicted_probs(MATCHES[0], DEFAULT_CONFIG)
    assert abs(sum(p) - 1.0) < 1e-9


def test_evaluate_lower_for_correct_direction():
    # 올바른 방향(β1>0)이 뒤집힌 방향(β1<0)보다 RPS 가 낮다
    forward = evaluate(MATCHES, DEFAULT_CONFIG)
    backward = evaluate(MATCHES, replace(DEFAULT_CONFIG, beta1=-DEFAULT_CONFIG.beta1))
    assert forward < backward


def test_backtest_report():
    rep = backtest(MATCHES, DEFAULT_CONFIG)
    assert rep.n == len(MATCHES)
    assert 0.0 <= rep.rps <= 1.0
    assert 0.0 <= rep.accuracy <= 1.0
    assert rep.brier >= 0.0


def test_backtest_empty():
    rep = backtest([], DEFAULT_CONFIG)
    assert rep.n == 0 and rep.rps == 0.0


def test_fit_minimizes_over_grid():
    best_cfg, best_score = fit(MATCHES)
    # 그리드 내 최소이므로 임의 그리드 점보다 작거나 같다
    arbitrary = evaluate(MATCHES, replace(DEFAULT_CONFIG, beta1=0.20, rho=0.0))
    assert best_score <= arbitrary + 1e-12
    # 강팀이 이기는 데이터 → 양의 β1 선택
    assert best_cfg.beta1 >= 0.40


def test_fit_improves_accuracy():
    best_cfg, _ = fit(MATCHES)
    # 명확한 데이터에서 비무승부 경기는 모두 맞춰야 한다
    decisive = [m for m in MATCHES if m.result_index != 1]
    rep = backtest(decisive, best_cfg)
    assert rep.accuracy == 1.0
