"""모델 보정·백테스트 — 과거 경기로 상수(β1, ρ 등)를 피팅하고 예측 품질을 평가.

설계 불변식 #1 유지: 평가도 스코어 매트릭스에서 승무패를 읽는다.
순수 함수 — 합성/실측 데이터로 한도 소모 없이 백테스트 가능.
참고: 기획서 §9(향후), 아키텍처 §10.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from .config import DEFAULT_CONFIG, ModelConfig
from .elo import elo_to_lambda
from .metrics import Probs, brier, is_correct, log_loss, rps
from .score_matrix import outcome_probabilities, score_matrix


@dataclass(frozen=True)
class HistoricalMatch:
    """과거 경기 한 건 — 레이팅과 실제 스코어."""

    rating_a: float
    rating_b: float
    goals_a: int
    goals_b: int
    h_a: float = 0.0
    h_b: float = 0.0

    @property
    def result_index(self) -> int:
        """0=A승, 1=무, 2=B승."""
        if self.goals_a > self.goals_b:
            return 0
        if self.goals_a == self.goals_b:
            return 1
        return 2


def predicted_probs(match: HistoricalMatch, cfg: ModelConfig) -> Probs:
    """경기의 예측 확률 (A승, 무, B승) — 매트릭스에서 산출."""
    lam_a, lam_b = elo_to_lambda(match.rating_a, match.rating_b, match.h_a, match.h_b, cfg)
    o = outcome_probabilities(score_matrix(lam_a, lam_b, cfg))
    return o.a_win, o.draw, o.b_win


def evaluate(
    matches: Iterable[HistoricalMatch],
    cfg: ModelConfig = DEFAULT_CONFIG,
    metric: Callable[[Probs, int], float] = rps,
) -> float:
    """주어진 설정으로 경기들의 평균 메트릭(기본 RPS). 낮을수록 좋음."""
    total = 0.0
    n = 0
    for m in matches:
        total += metric(predicted_probs(m, cfg), m.result_index)
        n += 1
    return total / n if n else 0.0


@dataclass(frozen=True)
class BacktestReport:
    n: int
    rps: float
    brier: float
    log_loss: float
    accuracy: float


def backtest(matches: list[HistoricalMatch], cfg: ModelConfig = DEFAULT_CONFIG) -> BacktestReport:
    """여러 지표로 백테스트 리포트 산출."""
    n = len(matches)
    if n == 0:
        return BacktestReport(0, 0.0, 0.0, 0.0, 0.0)
    s_rps = s_brier = s_ll = correct = 0.0
    for m in matches:
        p = predicted_probs(m, cfg)
        r = m.result_index
        s_rps += rps(p, r)
        s_brier += brier(p, r)
        s_ll += log_loss(p, r)
        correct += 1.0 if is_correct(p, r) else 0.0
    return BacktestReport(n, s_rps / n, s_brier / n, s_ll / n, correct / n)


def _frange(start: float, stop: float, step: float) -> list[float]:
    out = []
    x = start
    # 부동소수 누적 오차 방지: step 의 절반 여유
    while x <= stop + step / 2:
        out.append(round(x, 6))
        x += step
    return out


def fit(
    matches: list[HistoricalMatch],
    cfg: ModelConfig = DEFAULT_CONFIG,
    beta1_grid: list[float] | None = None,
    rho_grid: list[float] | None = None,
    metric: Callable[[Probs, int], float] = rps,
) -> tuple[ModelConfig, float]:
    """β1·ρ 그리드서치로 메트릭을 최소화하는 ModelConfig 탐색.

    (best_cfg, best_score) 반환. 다른 상수는 cfg 값을 유지.
    """
    beta1_grid = beta1_grid if beta1_grid is not None else _frange(0.20, 0.70, 0.05)
    rho_grid = rho_grid if rho_grid is not None else _frange(-0.20, 0.0, 0.02)

    best_cfg = cfg
    best_score = float("inf")
    for b1 in beta1_grid:
        for rho in rho_grid:
            trial = replace(cfg, beta1=b1, rho=rho)
            score = evaluate(matches, trial, metric)
            if score < best_score:
                best_score = score
                best_cfg = trial
    return best_cfg, best_score
