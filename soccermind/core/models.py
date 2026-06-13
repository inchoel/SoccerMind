"""도메인 데이터 모델. 참고: 아키텍처 §7."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResolvedTeam:
    """정규화된 팀 — 표준키(ISO alpha-3) + 소스별 식별자."""

    key: str  # ISO 3166-1 alpha-3, 예: "KOR"
    display: str  # 표시명, 예: "대한민국"
    elo_name: str | None = None  # eloratings.net 표기
    fd_id: int | None = None  # football-data.org team id
    api_football_id: int | None = None  # API-Football team id
    wikipedia: str | None = None  # Wikipedia 문서 제목


@dataclass(frozen=True)
class Ambiguous:
    """정규화 실패 — 후보 제안."""

    query: str
    candidates: list[ResolvedTeam] = field(default_factory=list)


@dataclass
class PlayerStat:
    """선수 득점 통계 (득점자 모델 입력)."""

    name: str
    intl_goals: int = 0  # 통산 A매치 득점
    matches: int = 0  # 통산 A매치 출전
    recent_goals: int = 0  # 최근 윈도우 득점
    recent_matches: int = 0  # 최근 윈도우 출전
    is_pen_taker: bool = False  # 지정 페널티 키커 여부
    availability: float = 1.0  # 출전 가능도 [0,1]: 1=확실한 선발, 0=결장
    position: str = ""  # 포지션 (예: "Goalkeeper", "Offence") — 골키퍼 득점자 제외용

    @property
    def is_goalkeeper(self) -> bool:
        return self.position.lower().startswith("goal")


@dataclass
class PartialTeamData:
    """한 Provider 가 반환하는 부분 데이터. 오케스트레이터가 병합한다."""

    source: str
    elo: float | None = None
    squad: list[PlayerStat] = field(default_factory=list)
    is_host: bool = False
    context: dict = field(default_factory=dict)


@dataclass
class TeamData:
    """한 팀의 수집·병합된 데이터."""

    team: ResolvedTeam
    elo: float
    squad: list[PlayerStat] = field(default_factory=list)
    is_host: bool = False
    context: dict = field(default_factory=dict)  # 부상/폼 등 LLM 컨텍스트


@dataclass(frozen=True)
class ScorerProb:
    name: str
    xg: float  # 기대 득점
    p_score: float  # 1골 이상 득점 확률


@dataclass(frozen=True)
class Prediction:
    """최종 예측 결과."""

    team_a: ResolvedTeam
    team_b: ResolvedTeam
    a_win: float
    draw: float
    b_win: float
    scoreline: tuple[int, int]
    scoreline_prob: float
    top_scorelines: list[tuple[int, int, float]]
    scorers_a: list[ScorerProb]
    scorers_b: list[ScorerProb]
    explanation: str
    meta: dict = field(default_factory=dict)

    @property
    def winner(self) -> ResolvedTeam | None:
        """최빈 결과가 무승부면 None."""
        best = max(self.a_win, self.draw, self.b_win)
        if best == self.draw:
            return None
        return self.team_a if self.a_win > self.b_win else self.team_b
