"""Elo replay — 결과를 시간순으로 재생하며 경기 전 레이팅을 재구성.

외부 과거 Elo 없이, 결과만으로 각 경기의 경기 전 레이팅을 얻어 보정 입력(HistoricalMatch)
을 만든다. World Football Elo 표준 업데이트(K·G·(W−W_e)) 사용. 결정적·재현 가능.
참고: 기획서 §9, 아키텍처 §10. 보정은 [[calibration]].
"""

from __future__ import annotations

from dataclasses import dataclass

from .calibration import HistoricalMatch
from .config import DEFAULT_CONFIG, ModelConfig
from .elo import goal_diff_multiplier, update_rating, win_expectancy

# 대회 가중치 K (World Football Elo)
K_WORLD_CUP = 60.0
K_CONTINENTAL = 50.0
K_QUALIFIER = 40.0
K_MINOR = 30.0
K_FRIENDLY = 20.0


@dataclass(frozen=True)
class MatchResult:
    """시간순 경기 결과 — replay 입력. team_a/team_b 는 식별자(이름/키)."""

    team_a: str
    team_b: str
    goals_a: int
    goals_b: int
    k_weight: float = K_WORLD_CUP
    home_a: bool = False  # team_a 홈 (아니면 중립)
    home_b: bool = False
    date: str | None = None  # 정렬·추적용 (ISO 권장)


def replay(
    results: list[MatchResult],
    base_rating: float = 1500.0,
    cfg: ModelConfig = DEFAULT_CONFIG,
) -> tuple[dict[str, float], list[HistoricalMatch]]:
    """결과를 순서대로 재생 → (최종 레이팅 맵, 경기별 HistoricalMatch[경기 전 레이팅]).

    HistoricalMatch 는 각 경기의 '경기 전' 레이팅을 담아 보정(fit/backtest)에 바로 쓰인다.
    """
    ratings: dict[str, float] = {}
    matches: list[HistoricalMatch] = []

    for r in results:
        ra = ratings.get(r.team_a, base_rating)
        rb = ratings.get(r.team_b, base_rating)
        h_a = cfg.host_advantage if r.home_a else 0.0
        h_b = cfg.host_advantage if r.home_b else 0.0

        # 경기 전 레이팅을 보정 입력으로 기록
        matches.append(
            HistoricalMatch(rating_a=ra, rating_b=rb, goals_a=r.goals_a,
                            goals_b=r.goals_b, h_a=h_a, h_b=h_b)
        )

        # World Football Elo 업데이트 (제로섬)
        w_a = 1.0 if r.goals_a > r.goals_b else (0.5 if r.goals_a == r.goals_b else 0.0)
        we_a = win_expectancy(ra, rb, h_a - h_b)
        g = goal_diff_multiplier(r.goals_a - r.goals_b)
        ratings[r.team_a] = update_rating(ra, w_a, we_a, r.k_weight, g)
        ratings[r.team_b] = update_rating(rb, 1.0 - w_a, 1.0 - we_a, r.k_weight, g)

    return ratings, matches
