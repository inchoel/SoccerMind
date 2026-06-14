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
    elo = FakeEloProvider({"BR": 2024.0, "KR": 1745.0})
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


def test_scoreline_consistent_with_winner():
    # 승리 예상과 스코어가 모순되지 않아야 (승 예상인데 1-1 방지)
    elo = FakeEloProvider({"BR": 2100.0, "KR": 1600.0})
    svc = PredictionService(providers=[elo])
    pred = svc.predict("브라질", "대한민국")
    assert pred.winner.key == "BRA"
    assert pred.scoreline[0] > pred.scoreline[1]  # 헤드라인 스코어도 A 우세


def test_meta_includes_analysis_sections():
    svc = _service()
    pred = svc.predict("브라질", "대한민국")
    an = pred.meta["analysis"]
    assert "notable" in an and "risks" in an and "watch_points" in an
    assert isinstance(an["watch_points"], list)


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
    elo = FakeEloProvider({"BR": 2024.0})  # 한국 Elo 없음
    svc = PredictionService(providers=[elo])
    pred = svc.predict("브라질", "대한민국")
    assert any("Elo 미상" in w for w in pred.meta["warnings"])
    # 그래도 예측은 생성됨 (graceful degradation)
    assert abs(pred.a_win + pred.draw + pred.b_win - 1.0) < 1e-9


def test_host_advantage_changes_lambda():
    elo = FakeEloProvider({"BR": 1800.0, "KR": 1800.0})
    svc = PredictionService(providers=[elo])
    neutral = svc.predict("브라질", "대한민국")
    hosted = svc.predict("브라질", "대한민국", PredictOptions(host_key="BRA"))
    # 개최국 보정으로 브라질 승률 상승
    assert hosted.a_win > neutral.a_win


def test_tournament_championship_probs():
    elo = FakeEloProvider({"BR": 2024.0, "KR": 1745.0,
                           "JP": 1750.0, "AR": 2115.0})
    svc = PredictionService(providers=[elo])
    res = svc.tournament(["브라질", "대한민국", "일본", "아르헨티나"])
    names = [n for n, _ in res]
    assert set(names) == {"브라질", "대한민국", "일본", "아르헨티나"}
    assert abs(sum(p for _, p in res) - 1.0) < 1e-9
    # 최강(아르헨티나)이 우승확률 1위
    assert res[0][0] == "아르헨티나"


def test_tournament_invalid_count_raises():
    elo = FakeEloProvider({"BR": 2024.0, "KR": 1745.0})
    svc = PredictionService(providers=[elo])
    with pytest.raises(ValueError):
        svc.tournament(["브라질", "대한민국", "일본"])  # 3팀 (2의 거듭제곱 아님)


def test_meta_reports_elo_and_only_contributing_sources():
    # 참조 데이터 투명성: meta.elo + 실제로 기여한 provider 만 sources_used 에
    class EmptyButAvailable(DataProvider):
        name = "empty"

        def available(self):
            return True

        def fetch(self, team):
            return PartialTeamData(source="empty")  # 빈 응답 (기여 없음)

    elo = FakeEloProvider({"BR": 2024.0, "KR": 1745.0})
    svc = PredictionService(providers=[elo, EmptyButAvailable()])
    pred = svc.predict("브라질", "대한민국")
    assert pred.meta["elo"]["a"] == 2024.0
    assert pred.meta["elo"]["b"] == 1745.0
    # Elo provider 는 기여 → 목록에, 빈 provider 는 제외
    assert "fake_elo" in pred.meta["sources_used"]["a"]
    assert "empty" not in pred.meta["sources_used"]["a"]


def test_unavailable_provider_skipped():
    class Down(DataProvider):
        name = "down"

        def available(self) -> bool:
            return False

        def fetch(self, team):
            raise AssertionError("불가용 provider 는 호출되면 안 됨")

    elo = FakeEloProvider({"BR": 2024.0, "KR": 1745.0})
    svc = PredictionService(providers=[Down(), elo])
    pred = svc.predict("브라질", "대한민국")  # 예외 없이 동작
    assert pred.meta["augmenter"] == "fallback"
