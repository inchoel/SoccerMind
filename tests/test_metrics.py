"""예측 메트릭 검증 (RPS/Brier/log-loss/accuracy)."""

import math

from soccermind.engine.metrics import brier, is_correct, log_loss, rps


def test_rps_perfect_is_zero():
    assert rps((1.0, 0.0, 0.0), 0) == 0.0
    assert rps((0.0, 1.0, 0.0), 1) == 0.0
    assert rps((0.0, 0.0, 1.0), 2) == 0.0


def test_rps_worst_case():
    # A승을 0%로 예측했는데 A가 이김 → 최대 1.0
    assert math.isclose(rps((0.0, 0.0, 1.0), 0), 1.0)


def test_rps_confident_wrong_worse_than_uncertain():
    confident_wrong = rps((0.0, 0.0, 1.0), 0)
    uncertain = rps((0.34, 0.33, 0.33), 0)
    assert confident_wrong > uncertain


def test_rps_respects_ordinal_distance():
    # B승 예측이 틀렸을 때, 실제가 무(인접)보다 A승(먼쪽)일 때 RPS 가 더 크다
    near = rps((0.0, 0.0, 1.0), 1)  # 실제 무
    far = rps((0.0, 0.0, 1.0), 0)   # 실제 A승
    assert far > near


def test_brier_perfect_and_worst():
    assert brier((1.0, 0.0, 0.0), 0) == 0.0
    assert math.isclose(brier((0.0, 0.0, 1.0), 0), 2.0)


def test_log_loss():
    assert math.isclose(log_loss((1.0, 0.0, 0.0), 0), 0.0, abs_tol=1e-9)
    assert log_loss((0.5, 0.25, 0.25), 0) > 0


def test_is_correct():
    assert is_correct((0.6, 0.3, 0.1), 0) is True
    assert is_correct((0.1, 0.3, 0.6), 0) is False
    assert is_correct((0.2, 0.5, 0.3), 1) is True
