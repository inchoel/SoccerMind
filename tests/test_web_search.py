"""웹검색 부상/결장 속보 검증 — 파싱 순수 + 검색 주입 (네트워크 없음)."""

from soccermind.core.models import PartialTeamData, ResolvedTeam
from soccermind.core.name_resolver import NameResolver
from soccermind.core.orchestrator import PredictionService
from soccermind.data.base import DataProvider
from soccermind.data.cache import DiskCache
from soccermind.data.web_search import (
    WebSearchProvider,
    extract_injury_notes,
    parse_ddg_results,
)

R = NameResolver()

DDG_HTML = """
<div class="result">
  <a class="result__snippet" href="x">Son Heung-min has been <b>ruled out</b> with a hamstring injury.</a>
</div>
<div class="result">
  <a class="result__snippet" href="y">South Korea announce 26-man squad for the World Cup.</a>
</div>
<div class="result">
  <a class="result__snippet" href="z">Kim Min-jae is suspended after yellow card accumulation.</a>
</div>
"""


def test_parse_ddg_results():
    snippets = parse_ddg_results(DDG_HTML)
    assert len(snippets) == 3
    assert "ruled out" in snippets[0]
    assert "<b>" not in snippets[0]  # 태그 제거


def test_extract_injury_notes_filters_and_limits():
    snippets = parse_ddg_results(DDG_HTML)
    notes = extract_injury_notes(snippets)
    # 부상/징계 2건만 (스쿼드 발표는 제외)
    assert len(notes) == 2
    assert any("ruled out" in n for n in notes)
    assert any("suspended" in n for n in notes)
    assert all("announce 26-man" not in n for n in notes)


def test_extract_dedupes():
    dup = ["Player X ruled out with injury", "Player X ruled out with injury"]
    assert len(extract_injury_notes(dup)) == 1


def test_provider_disabled_by_default():
    p = WebSearchProvider(enabled=False)
    assert p.available() is False
    assert p.fetch(R.resolve("대한민국")).context == {}


def test_provider_enabled_with_injected_search(tmp_path):
    def fake_search(q):
        assert "national football team" in q
        return parse_ddg_results(DDG_HTML)

    p = WebSearchProvider(enabled=True, search=fake_search, cache=DiskCache(tmp_path))
    assert p.available() is True
    partial = p.fetch(R.resolve("대한민국"))
    assert partial.source == "web_search"
    assert len(partial.context["injuries"]) == 2


def test_provider_search_failure_graceful(tmp_path):
    def boom(q):
        raise RuntimeError("network down")

    p = WebSearchProvider(enabled=True, search=boom, cache=DiskCache(tmp_path))
    assert p.fetch(R.resolve("대한민국")).context == {}  # 예외 대신 빈 컨텍스트


def test_injuries_surfaced_in_prediction_meta(tmp_path):
    class FakeElo(DataProvider):
        name = "elo"

        def available(self):
            return True

        def fetch(self, team: ResolvedTeam):
            return PartialTeamData(source="elo", elo={"Korea South": 1745.0,
                                                      "Japan": 1750.0}.get(team.elo_name))

    ws = WebSearchProvider(enabled=True, search=lambda q: parse_ddg_results(DDG_HTML),
                           cache=DiskCache(tmp_path))
    svc = PredictionService(providers=[FakeElo(), ws])
    pred = svc.predict("대한민국", "일본")
    assert len(pred.meta["injuries"]["a"]) == 2
