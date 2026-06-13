"""PredictionService — 전체 예측 파이프라인 조율 (아키텍처 §8).

정규화 → 수집(병합) → 통계 엔진 → 득점자 → LLM 보강 → 예측 조립.
임의 대진 지원: 두 팀을 각각 독립 조회 (설계 불변식 #6).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.base import DataProvider
from ..engine.config import DEFAULT_CONFIG, ModelConfig
from ..engine.elo import elo_to_lambda, venue_adjustment
from ..engine.score_matrix import (
    most_likely_scoreline,
    outcome_probabilities,
    score_matrix,
    top_scorelines,
)
from ..engine.scorers import rank_scorers
from ..engine.tournament import TournamentTeam, championship_probabilities
from ..llm.base import AugmentInput, Augmenter
from ..llm.fallback import FallbackAugmenter
from .models import (
    Ambiguous,
    PartialTeamData,
    Prediction,
    ResolvedTeam,
    TeamData,
)
from .name_resolver import NameResolver

DEFAULT_RATING = 1500.0  # Elo 미상 팀의 중립 기본값 (meta 에 경고 기록)


class ResolutionError(Exception):
    """국가명 정규화 실패."""

    def __init__(self, query: str, candidates: list[ResolvedTeam]):
        self.query = query
        self.candidates = candidates
        names = ", ".join(c.display for c in candidates) or "없음"
        super().__init__(f"'{query}' 을(를) 인식하지 못했습니다. 후보: {names}")


@dataclass
class PredictOptions:
    host_key: str | None = None  # 개최국 표준키 (있으면 홈 어드밴티지)


class PredictionService:
    def __init__(
        self,
        providers: list[DataProvider],
        resolver: NameResolver | None = None,
        augmenter: Augmenter | None = None,
        cfg: ModelConfig = DEFAULT_CONFIG,
    ) -> None:
        self.providers = providers
        self.resolver = resolver or NameResolver()
        self.augmenter = augmenter
        self.cfg = cfg
        self._fallback = FallbackAugmenter()

    def _resolve(self, raw: str) -> ResolvedTeam:
        r = self.resolver.resolve(raw)
        if isinstance(r, Ambiguous):
            raise ResolutionError(r.query, r.candidates)
        return r

    def gather(self, team: ResolvedTeam, is_host: bool = False) -> tuple[TeamData, list[str]]:
        """각 available provider 에서 부분 데이터를 모아 병합. (TeamData, 경고목록)."""
        elo: float | None = None
        squad = []
        context: dict = {}
        used: list[str] = []
        warnings: list[str] = []

        for p in self.providers:
            if not p.available():
                continue
            try:
                partial: PartialTeamData = p.fetch(team)
            except Exception:
                continue
            used.append(p.name)
            if elo is None and partial.elo is not None:
                elo = partial.elo
            if not squad and partial.squad:
                squad = partial.squad
            context.update(partial.context)

        if elo is None:
            elo = DEFAULT_RATING
            warnings.append(f"{team.display}: Elo 미상, 기본값 {DEFAULT_RATING} 사용")

        context["sources_used"] = used
        return TeamData(team=team, elo=elo, squad=squad, is_host=is_host, context=context), warnings

    def predict(
        self, raw_a: str, raw_b: str, opts: PredictOptions | None = None
    ) -> Prediction:
        opts = opts or PredictOptions()
        a = self._resolve(raw_a)
        b = self._resolve(raw_b)

        td_a, warn_a = self.gather(a, is_host=(opts.host_key == a.key))
        td_b, warn_b = self.gather(b, is_host=(opts.host_key == b.key))

        # 통계 엔진 (불변식 #1)
        h_a, h_b = venue_adjustment(td_a.is_host, td_b.is_host, self.cfg)
        lam_a, lam_b = elo_to_lambda(td_a.elo, td_b.elo, h_a, h_b, self.cfg)
        matrix = score_matrix(lam_a, lam_b, self.cfg)
        outcome = outcome_probabilities(matrix)
        x, y, sp = most_likely_scoreline(matrix)
        tops = top_scorelines(matrix, n=5)

        scorers_a = rank_scorers(lam_a, td_a.squad, cfg=self.cfg)
        scorers_b = rank_scorers(lam_b, td_b.squad, cfg=self.cfg)

        # LLM 보강 (없으면 폴백) — 확률·스코어는 통과만, 득점자/해설만 갱신
        aug = self.augmenter if (self.augmenter and self.augmenter.available()) else self._fallback
        result = aug.run(
            AugmentInput(
                team_a=a, team_b=b, lam_a=lam_a, lam_b=lam_b,
                outcome=outcome, scoreline=(x, y, sp), top_scorelines=tops,
                scorers_a=scorers_a, scorers_b=scorers_b,
                squad_a=td_a.squad, squad_b=td_b.squad,
                context={"a": td_a.context, "b": td_b.context},
            )
        )

        return Prediction(
            team_a=a, team_b=b,
            a_win=outcome.a_win, draw=outcome.draw, b_win=outcome.b_win,
            scoreline=(x, y), scoreline_prob=sp, top_scorelines=tops,
            scorers_a=result.scorers_a, scorers_b=result.scorers_b,
            explanation=result.explanation,
            meta={
                "augmenter": getattr(aug, "name", "augmenter"),
                "lambda": {"a": round(lam_a, 3), "b": round(lam_b, 3)},
                "sources_used": {"a": td_a.context.get("sources_used", []),
                                 "b": td_b.context.get("sources_used", [])},
                "form": {"a": td_a.context.get("form", []),
                         "b": td_b.context.get("form", [])},
                "warnings": warn_a + warn_b,
            },
        )

    def tournament(self, raw_names: list[str]) -> list[tuple[str, float]]:
        """녹아웃 토너먼트(2의 거듭제곱 팀, 시드 순) 우승 확률.

        각 팀을 독립 조회해 Elo 를 모으고 정확한 브래킷 DP 로 산출.
        """
        teams = []
        for raw in raw_names:
            t = self._resolve(raw)
            td, _ = self.gather(t)
            teams.append(TournamentTeam(name=t.display, rating=td.elo))
        return championship_probabilities(teams, self.cfg)
