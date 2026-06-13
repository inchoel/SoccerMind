"""Wikipedia 스쿼드 provider 검증 — 위키텍스트 파싱 + fetch 주입 + 통합."""

from soccermind.core.models import PartialTeamData, ResolvedTeam
from soccermind.core.name_resolver import NameResolver
from soccermind.core.orchestrator import PredictionService
from soccermind.data.base import DataProvider
from soccermind.data.cache import DiskCache
from soccermind.data.wikipedia import (
    WikipediaProvider,
    parse_recent_form,
    parse_squad_from_wikitext,
    team_token,
)

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


# 실제 문서가 쓰는 형식: {{nat fs g player}} + 내부 중첩 템플릿({{birth date and age}})
NAT_FS_G_WIKITEXT = """
{{nat fs start}}
{{nat fs g player|pos=GK|no=1|name=[[Kim Seung-gyu]]|age={{birth date and age|1990|9|30|df=y}}|caps=88|goals=0|club=...}}
{{nat fs g player|pos=FW|no=7|name=[[Son Heung-min]]|age={{birth date and age|1992|7|8|df=y}}|caps=130|goals=48|club=...}}
{{nat fs g player|pos=MF|no=10|name=[[Lee Kang-in|Lee]]|age={{birth date and age|2001|2|19|df=y}}|caps=30|goals=5|club=...}}
{{nat fs end}}
"""


def test_parse_nat_fs_g_player_with_nested_templates():
    # 중첩 {{birth date and age}} 때문에 단순 정규식은 잘렸던 회귀 케이스
    squad = parse_squad_from_wikitext(NAT_FS_G_WIKITEXT)
    assert len(squad) == 3
    son = next(p for p in squad if p.name == "Son Heung-min")
    assert son.intl_goals == 48 and son.matches == 130
    assert son.position == "Offence"
    gk = next(p for p in squad if p.name == "Kim Seung-gyu")
    assert gk.is_goalkeeper is True
    assert any(p.name == "Lee" for p in squad)  # [[A|B]] → B


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


FORM_WIKITEXT = """
== Results and fixtures ==
{{Football box collapsible
|date=5 June 2026
|team1={{flagicon|KOR}} South Korea
|score=2–1
|team2=Japan {{flagicon|JPN}}
|goals1={{goal|23}} Son
|goals2={{goal|70}} Mitoma
}}
{{Football box collapsible
|date=9 June 2026
|team1=Brazil
|score=0–0
|team2=South Korea
}}
{{Football box collapsible
|date=12 June 2026
|team1=South Korea
|score=1–3
|team2=Spain
}}
"""


def test_team_token():
    assert team_token("South Korea national football team") == "South Korea"
    assert team_token("United States men's national soccer team") == "United States"


def test_parse_recent_form_orders_recent_first():
    form = parse_recent_form(FORM_WIKITEXT, "South Korea")
    assert len(form) == 3
    # 문서 마지막(최신)이 맨 앞
    assert form[0] == "L 1-3 vs Spain"
    assert form[1] == "D 0-0 vs Brazil"
    assert form[2] == "W 2-1 vs Japan"  # 상대 플래그아이콘 제거됨


def test_parse_recent_form_respects_limit():
    form = parse_recent_form(FORM_WIKITEXT, "South Korea", limit=2)
    assert form == ["L 1-3 vs Spain", "D 0-0 vs Brazil"]


def test_parse_recent_form_none_for_unknown_team():
    assert parse_recent_form(FORM_WIKITEXT, "Argentina") == []


def test_provider_populates_form_context(tmp_path):
    p = WikipediaProvider(fetch_wikitext=lambda t: FORM_WIKITEXT, cache=DiskCache(tmp_path))
    partial = p.fetch(R.resolve("대한민국"))
    assert partial.context.get("form")
    assert partial.context["form"][0] == "L 1-3 vs Spain"


def test_form_surfaced_in_prediction_meta(tmp_path):
    class FakeElo(DataProvider):
        name = "elo"

        def available(self):
            return True

        def fetch(self, team: ResolvedTeam):
            return PartialTeamData(source="elo", elo={"Korea South": 1745.0,
                                                      "Japan": 1750.0}.get(team.elo_name))

    wiki = WikipediaProvider(fetch_wikitext=lambda t: FORM_WIKITEXT, cache=DiskCache(tmp_path))
    svc = PredictionService(providers=[FakeElo(), wiki])
    pred = svc.predict("대한민국", "일본")
    assert pred.meta["form"]["a"][0] == "L 1-3 vs Spain"


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
