"""오케스트레이터 end-to-end 검증 — 가짜 provider 로 네트워크 없이."""

import pytest

from soccermind.core.models import PartialTeamData, PlayerStat, ResolvedTeam
from soccermind.core.orchestrator import PredictOptions, PredictionService, ResolutionError
from soccermind.data.base import DataProvider


class FakeEloProvider(DataProvider):
    name = "fake_elo"

    def __init__(self, ratings: dict[str, float]):
        self.ratings = ratings  # elo_name -> rating

    def available(self) -> bool:
        return True

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        return PartialTeamData(source=self.name, elo=self.ratings.get(team.elo_name))


class FakeSquadProvider(DataProvider):
    name = "fake_squad"

    def __init__(self, squads: dict[str, list[PlayerStat]]):
        self.squads = squads  # team key -> squad

    def available(self) -> bool:
        return True

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        return PartialTeamData(source=self.name, squad=self.squads.get(team.key, []))


def _service():
    elo = FakeEloProvider({"Brazil": 2024.0, "Korea South": 1745.0})
    squads = FakeSquadProvider(
        {
            "BRA": [PlayerStat("Vinicius", intl_goals=10, matches=30, position="Offence"),
                    PlayerStat("Alisson", position="Goalkeeper")],
            "KOR": [PlayerStat("Son", intl_goals=40, matches=120, position="Offence")],
        }
    )
    return PredictionService(providers=[elo, squads])


def test_end_to_end_prediction():
    svc = _service()
    pred = svc.predict("브라질", "대한민국")
    assert pred.team_a.key == "BRA"
    assert pred.team_b.key == "KOR"
    # 확률 합 = 1
    assert abs(pred.a_win + pred.draw + pred.b_win - 1.0) < 1e-9
    # 브라질이 더 강하므로 a_win > b_win
    assert pred.a_win > pred.b_win
    # 스코어라인 유효
    assert len(pred.scoreline) == 2
    # 해설 존재
    assert pred.explanation
    assert pred.meta["augmenter"] == "fallback"


def test_winner_property():
    svc = _service()
    pred = svc.predict("브라질", "대한민국")
    assert pred.winner is not None
    assert pred.winner.key == "BRA"


def test_scorers_exclude_goalkeeper():
    svc = _service()
    pred = svc.predict("브라질", "대한민국")
    names = [s.name for s in pred.scorers_a]
    assert "Alisson" not in names  # 골키퍼 제외
    assert "Vinicius" in names


def test_arbitrary_matchup_supported():
    # 실제 일정에 없는 임의 대진도 동작 (불변식 #6)
    svc = _service()
    pred = svc.predict("대한민국", "브라질")
    assert pred.team_a.key == "KOR" and pred.team_b.key == "BRA"


def test_resolution_error_on_unknown():
    svc = _service()
    with pytest.raises(ResolutionError) as exc:
        svc.predict("Atlantis", "브라질")
    assert exc.value.query == "Atlantis"


def test_missing_elo_uses_default_with_warning():
    # Elo provider 가 한 팀만 알고 있을 때
    elo = FakeEloProvider({"Brazil": 2024.0})  # 한국 Elo 없음
    svc = PredictionService(providers=[elo])
    pred = svc.predict("브라질", "대한민국")
    assert any("Elo 미상" in w for w in pred.meta["warnings"])
    # 그래도 예측은 생성됨 (graceful degradation)
    assert abs(pred.a_win + pred.draw + pred.b_win - 1.0) < 1e-9


def test_host_advantage_changes_lambda():
    elo = FakeEloProvider({"Brazil": 1800.0, "Korea South": 1800.0})
    svc = PredictionService(providers=[elo])
    neutral = svc.predict("브라질", "대한민국")
    hosted = svc.predict("브라질", "대한민국", PredictOptions(host_key="BRA"))
    # 개최국 보정으로 브라질 승률 상승
    assert hosted.a_win > neutral.a_win


def test_unavailable_provider_skipped():
    class Down(DataProvider):
        name = "down"

        def available(self) -> bool:
            return False

        def fetch(self, team):
            raise AssertionError("불가용 provider 는 호출되면 안 됨")

    elo = FakeEloProvider({"Brazil": 2024.0, "Korea South": 1745.0})
    svc = PredictionService(providers=[Down(), elo])
    pred = svc.predict("브라질", "대한민국")  # 예외 없이 동작
    assert pred.meta["augmenter"] == "fallback"
