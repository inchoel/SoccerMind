"""득점자 예측 — 선수별 기대득점(xG)과 득점 확률 랭킹.

xG_i = λ_team · s_i · a_i + pen_team · p_i
    s_i = 정규화된 득점지분 (장기 지분 w + 최근 폼 (1-w) 블렌드)
    a_i = 출전 가능도 [0,1]
    pen_team = 경기당 기대 페널티 × 전환율,  p_i = 페널티 키커이면 1
P(i 득점≥1) = 1 − exp(−xG_i)
참고: 아키텍처 §4.4, 기획서 F4.
"""

from __future__ import annotations

import math

from ..core.models import PlayerStat, ScorerProb
from .config import DEFAULT_CONFIG, ModelConfig


def _raw_share(p: PlayerStat, team_goals: int, cfg: ModelConfig) -> float:
    """장기 득점지분과 최근 득점률의 가중 블렌드 (정규화 전 raw 값)."""
    historical = (p.intl_goals / team_goals) if team_goals > 0 else 0.0
    recent = (p.recent_goals / p.recent_matches) if p.recent_matches > 0 else 0.0
    return cfg.form_weight * historical + (1.0 - cfg.form_weight) * recent


def rank_scorers(
    lam_team: float,
    squad: list[PlayerStat],
    top_n: int = 6,
    cfg: ModelConfig = DEFAULT_CONFIG,
) -> list[ScorerProb]:
    """팀의 기대 XI 에 대해 득점 확률 내림차순 상위 N명 반환."""
    available = [p for p in squad if p.availability > 0.0]
    if not available:
        return []

    team_goals = sum(p.intl_goals for p in available)
    raw = [_raw_share(p, team_goals, cfg) for p in available]
    raw_sum = sum(raw)

    pen = cfg.expected_penalties * cfg.penalty_conversion

    scorers: list[ScorerProb] = []
    for p, r in zip(available, raw):
        share = (r / raw_sum) if raw_sum > 0 else (1.0 / len(available))
        xg = lam_team * share * p.availability
        if p.is_pen_taker:
            xg += pen
        p_score = 1.0 - math.exp(-xg)
        scorers.append(ScorerProb(name=p.name, xg=xg, p_score=p_score))

    scorers.sort(key=lambda s: s.p_score, reverse=True)
    return scorers[:top_n]
