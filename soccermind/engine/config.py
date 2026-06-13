"""모델 보정 상수 — 한 곳에 집중 (코드에 하드코딩 금지).

기본값은 합리적 사전값(prior)이며, 향후 과거 경기로 피팅하여 재보정한다.
참고: 기획서 §8, 아키텍처 §4.4.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    # --- Elo → λ (기대득점) 변환 ---
    # T = 호각인 중립 경기의 기준 총득점. beta0 = log(T/2) 가 총득점을 앵커링한다.
    baseline_total_goals: float = 2.6
    # beta1 = Elo 격차가 득점 우위로 변환되는 강도. 사전값 0.40, 피팅 대상.
    beta1: float = 0.40

    # --- Dixon-Coles 저점수 보정 ---
    # rho < 0 이면 0-0, 1-1 쪽으로 질량 이동 → 무승부 과소예측 교정.
    rho: float = -0.05

    # --- 베뉴(home/neutral) 보정, Elo 점수 단위 ---
    # 월드컵은 중립 개최가 기본. 개최국만 축소된 홈 어드밴티지.
    host_advantage: float = 60.0

    # --- 득점자 모델 ---
    # 장기 득점지분 vs 최근 폼 가중치 (s_i 계산).
    form_weight: float = 0.6
    # 경기당 기대 페널티 횟수 × 전환율 (페널티 항).
    expected_penalties: float = 0.12
    penalty_conversion: float = 0.78

    # --- 스코어 매트릭스 격자 크기 ---
    max_goals: int = 10

    @property
    def beta0(self) -> float:
        """log(T/2) — 총득점 앵커."""
        return math.log(self.baseline_total_goals / 2.0)


# 기본 설정 싱글턴
DEFAULT_CONFIG = ModelConfig()
