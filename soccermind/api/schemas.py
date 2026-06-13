"""API 응답 Pydantic 스키마. 도메인 Prediction → 응답 변환."""

from __future__ import annotations

from pydantic import BaseModel

from ..core.models import Prediction


class TeamRef(BaseModel):
    key: str
    name: str


class WinnerOut(BaseModel):
    key: str | None  # 무승부면 None
    name: str | None
    confidence: float


class WDLOut(BaseModel):
    a_win: float
    draw: float
    b_win: float


class ScorelineOut(BaseModel):
    a: int
    b: int
    prob: float


class TopScoreline(BaseModel):
    score: str
    p: float


class ScorerOut(BaseModel):
    name: str
    p: float


class PredictionResponse(BaseModel):
    teams: dict[str, TeamRef]
    winner: WinnerOut
    wdl: WDLOut
    scoreline: ScorelineOut
    top_scorelines: list[TopScoreline]
    scorers: dict[str, list[ScorerOut]]
    explanation: str
    meta: dict


def to_response(pred: Prediction) -> PredictionResponse:
    winner = pred.winner
    best = max(pred.a_win, pred.draw, pred.b_win)
    return PredictionResponse(
        teams={
            "a": TeamRef(key=pred.team_a.key, name=pred.team_a.display),
            "b": TeamRef(key=pred.team_b.key, name=pred.team_b.display),
        },
        winner=WinnerOut(
            key=winner.key if winner else None,
            name=winner.display if winner else None,
            confidence=round(best, 3),
        ),
        wdl=WDLOut(a_win=round(pred.a_win, 3), draw=round(pred.draw, 3),
                   b_win=round(pred.b_win, 3)),
        scoreline=ScorelineOut(a=pred.scoreline[0], b=pred.scoreline[1],
                               prob=round(pred.scoreline_prob, 3)),
        top_scorelines=[TopScoreline(score=f"{x}-{y}", p=round(p, 3))
                        for x, y, p in pred.top_scorelines],
        scorers={
            "a": [ScorerOut(name=s.name, p=round(s.p_score, 3)) for s in pred.scorers_a],
            "b": [ScorerOut(name=s.name, p=round(s.p_score, 3)) for s in pred.scorers_b],
        },
        explanation=pred.explanation,
        meta=pred.meta,
    )


class TeamListItem(BaseModel):
    key: str
    name: str


class CandidateError(BaseModel):
    detail: str
    query: str
    candidates: list[TeamListItem]


class ChampionOut(BaseModel):
    name: str
    prob: float
