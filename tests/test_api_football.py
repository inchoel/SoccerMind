"""API-Football provider 검증 — 파싱 순수성 + fetch 주입 + 득점자 통합."""

from soccermind.core.models import PartialTeamData, ResolvedTeam
from soccermind.core.name_resolver import NameResolver
from soccermind.core.orchestrator import PredictionService
from soccermind.data.api_football import ApiFootballProvider, parse_players
from soccermind.data.base import DataProvider
from soccermind.data.cache import DiskCache

R = NameResolver()

PLAYERS_JSON = {
    "response": [
        {"player": {"name": "Son Heung-min"},
         "statistics": [{"games": {"appearences": 10, "position": "Attacker"},
                         "goals": {"total": 8}, "penalty": {"scored": 2}}]},
        {"player": {"name": "Hwang Hee-chan"},
         "statistics": [{"games": {"appearences": 9, "position": "Attacker"},
                         "goals": {"total": 3}, "penalty": {"scored": 0}}]},
        {"player": {"name": "Jo Hyeon-woo"},
         "statistics": [{"games": {"appearences": 11, "position": "Goalkeeper"},
                         "goals": {"total": 0}}]},
    ]
}


def test_parse_players():
    squad = parse_players(PLAYERS_JSON)
    assert len(squad) == 3
    son = next(p for p in squad if p.name == "Son Heung-min")
    assert son.intl_goals == 8
    assert son.matches == 10
    assert son.is_pen_taker is True
    gk = next(p for p in squad if p.name == "Jo Hyeon-woo")
    assert gk.is_goalkeeper is True
    assert gk.intl_goals == 0


def test_parse_players_empty():
    assert parse_players({}) == []
    assert parse_players({"response": None}) == []


def test_provider_unavailable_without_key():
    p = ApiFootballProvider(key="")
    assert p.available() is False
    assert p.fetch(R.resolve("대한민국")).squad == []


def test_provider_fetch_with_injected_json(tmp_path):
    def fake_json(url, key):
        assert "team=17" in url and "season=2026" in url
        assert key == "K"
        return PLAYERS_JSON

    p = ApiFootballProvider(key="K", fetch_json=fake_json, cache=DiskCache(tmp_path))
    assert p.available() is True
    partial = p.fetch(R.resolve("대한민국"))  # KOR api_football_id=17
    assert partial.source == "api_football"
    assert len(partial.squad) == 3


def test_provider_no_api_id_returns_empty(tmp_path):
    # 브라질은 api_football_id 미설정 → fetch 호출 없이 빈 데이터
    p = ApiFootballProvider(key="K", fetch_json=lambda u, k: PLAYERS_JSON,
                            cache=DiskCache(tmp_path))
    assert p.fetch(R.resolve("브라질")).squad == []


def test_scorer_ranking_uses_goal_stats(tmp_path):
    # 득점 통계가 있으면 균등이 아니라 득점순으로 랭킹된다
    class FakeElo(DataProvider):
        name = "elo"

        def available(self):
            return True

        def fetch(self, team: ResolvedTeam):
            ratings = {"Korea South": 1745.0, "Japan": 1750.0}
            return PartialTeamData(source="elo", elo=ratings.get(team.elo_name))

    apif = ApiFootballProvider(key="K", fetch_json=lambda u, k: PLAYERS_JSON,
                               cache=DiskCache(tmp_path))
    svc = PredictionService(providers=[FakeElo(), apif])
    pred = svc.predict("대한민국", "일본")  # team_a=KOR 이 API-Football 스쿼드 보유
    names = [s.name for s in pred.scorers_a]
    assert names[0] == "Son Heung-min"  # 최다 득점자 1위
    assert "Jo Hyeon-woo" not in names  # 골키퍼 제외
    # 균등이 아님 (손흥민 확률 > 황희찬)
    assert pred.scorers_a[0].p_score > pred.scorers_a[1].p_score
