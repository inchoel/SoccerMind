"""Wikipedia 스쿼드 provider 검증 — 위키텍스트 파싱 + fetch 주입 + 통합."""

from soccermind.core.models import PartialTeamData, ResolvedTeam
from soccermind.core.name_resolver import NameResolver
from soccermind.core.orchestrator import PredictionService
from soccermind.data.base import DataProvider
from soccermind.data.cache import DiskCache
from soccermind.data.wikipedia import WikipediaProvider, parse_squad_from_wikitext

R = NameResolver()

WIKITEXT = """
{{nat fs g start}}
{{nat fs player|no=1|pos=GK|name=[[Jo Hyeon-woo]]|caps=60|goals=0|club=...}}
{{nat fs player|no=7|pos=FW|name=Son Heung-min|caps=130|goals=48|club=...}}
{{nat fs player|no=10|pos=MF|name=[[Lee Kang-in|Lee]]|caps=30|goals=5}}
{{nat fs player|no=4|pos=DF|name=Kim Min-jae|caps=70|goals=2}}
{{nat fs end}}
"""


def test_parse_squad_from_wikitext():
    squad = parse_squad_from_wikitext(WIKITEXT)
    assert len(squad) == 4
    son = next(p for p in squad if p.name == "Son Heung-min")
    assert son.intl_goals == 48 and son.matches == 130
    assert son.position == "Offence"
    gk = next(p for p in squad if p.name == "Jo Hyeon-woo")
    assert gk.is_goalkeeper is True
    # [[A|B]] 링크는 표시명 B 로 정리
    assert any(p.name == "Lee" for p in squad)


def test_parse_empty():
    assert parse_squad_from_wikitext("") == []
    assert parse_squad_from_wikitext("본문에 선수 템플릿 없음") == []


def test_provider_always_available():
    assert WikipediaProvider().available() is True


def test_provider_no_wikipedia_title_returns_empty(tmp_path):
    # wikipedia 제목이 없는 팀은 빈 데이터 (현재 모든 팀에 있지만 방어적)
    p = WikipediaProvider(fetch_wikitext=lambda t: WIKITEXT, cache=DiskCache(tmp_path))
    team = ResolvedTeam(key="ZZZ", display="없음", wikipedia=None)
    assert p.fetch(team).squad == []


def test_provider_fetch_with_injection(tmp_path):
    calls = {"n": 0}

    def fake(title):
        calls["n"] += 1
        assert title == "South Korea national football team"
        return WIKITEXT

    p = WikipediaProvider(fetch_wikitext=fake, cache=DiskCache(tmp_path))
    partial = p.fetch(R.resolve("대한민국"))
    assert partial.source == "wikipedia"
    assert len(partial.squad) == 4
    # 캐시 적중 — 재호출 시 네트워크 미사용
    p.fetch(R.resolve("대한민국"))
    assert calls["n"] == 1


def test_covers_team_without_source_ids(tmp_path):
    # 브라질은 fd_id/api_football_id 가 없지만 Wikipedia 로 스쿼드 확보
    class FakeElo(DataProvider):
        name = "elo"

        def available(self):
            return True

        def fetch(self, team: ResolvedTeam):
            ratings = {"Brazil": 2024.0, "Korea South": 1745.0}
            return PartialTeamData(source="elo", elo=ratings.get(team.elo_name))

    wiki = WikipediaProvider(fetch_wikitext=lambda t: WIKITEXT, cache=DiskCache(tmp_path))
    svc = PredictionService(providers=[FakeElo(), wiki])
    pred = svc.predict("브라질", "대한민국")
    # 스쿼드를 확보해 득점자 목록이 비어있지 않고 득점순 정렬
    assert pred.scorers_a and pred.scorers_a[0].name == "Son Heung-min"
    assert all(s.name != "Jo Hyeon-woo" for s in pred.scorers_a)  # GK 제외
