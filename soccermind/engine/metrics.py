"""예측 평가 메트릭 — 순서형 결과(승/무/패) 채점.

확률 벡터 probs = (P(A승), P(무), P(B승)), 관측 인덱스 0=A승 / 1=무 / 2=B승.
RPS(순위확률점수)가 축구 예측의 표준 지표. 낮을수록 좋다 (RPS·Brier·log-loss).
"""

from __future__ import annotations

import math

Probs = tuple[float, float, float]


def _onehot(index: int) -> tuple[int, int, int]:
    e = [0, 0, 0]
    e[index] = 1
    return e[0], e[1], e[2]


def rps(probs: Probs, observed: int) -> float:
    """순위확률점수 (Ranked Probability Score). 순서형 3분류, 0~1, 낮을수록 좋음."""
    e = _onehot(observed)
    cum_p = cum_e = 0.0
    s = 0.0
    for k in range(3):
        cum_p += probs[k]
        cum_e += e[k]
        s += (cum_p - cum_e) ** 2
    return s / (3 - 1)


def brier(probs: Probs, observed: int) -> float:
    """다분류 브라이어 스코어 = Σ(p_k − e_k)². 0~2, 낮을수록 좋음."""
    e = _onehot(observed)
    return sum((probs[k] - e[k]) ** 2 for k in range(3))


def log_loss(probs: Probs, observed: int, eps: float = 1e-12) -> float:
    """관측 결과 확률의 음의 로그. 낮을수록 좋음."""
    p = max(probs[observed], eps)
    return -math.log(p)


def is_correct(probs: Probs, observed: int) -> bool:
    """최빈 예측(argmax)이 실제 결과와 일치하는가."""
    return max(range(3), key=lambda k: probs[k]) == observed
