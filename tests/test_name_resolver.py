"""국가명 정규화 검증 (설계 불변식 #4, 기획서 F1)."""

from soccermind.core.models import Ambiguous, ResolvedTeam
from soccermind.core.name_resolver import NameResolver

R = NameResolver()


def test_korean_display_name():
    r = R.resolve("대한민국")
    assert isinstance(r, ResolvedTeam)
    assert r.key == "KOR"


def test_korean_short_alias():
    assert R.resolve("한국").key == "KOR"


def test_english_aliases():
    for name in ["Korea", "South Korea", "korea republic"]:
        r = R.resolve(name)
        assert isinstance(r, ResolvedTeam) and r.key == "KOR"


def test_case_and_whitespace_insensitive():
    assert R.resolve("  BRAZIL  ").key == "BRA"


def test_typo_fuzzy_match():
    # 오타도 퍼지 매칭으로 흡수.
    assert R.resolve("brasil").key == "BRA"
    assert R.resolve("argentna").key == "ARG"


def test_source_identifiers_present():
    r = R.resolve("대한민국")
    assert r.elo_name == "Korea South"
    assert r.fd_id == 770
    assert r.wikipedia == "South Korea national football team"


def test_unknown_returns_ambiguous():
    r = R.resolve("Atlantis")
    assert isinstance(r, Ambiguous)
    assert r.query == "Atlantis"


def test_empty_returns_ambiguous():
    assert isinstance(R.resolve(""), Ambiguous)


def test_korea_north_south_distinct():
    assert R.resolve("북한").key == "PRK"
    assert R.resolve("남한").key == "KOR"


def test_all_teams_listed():
    teams = R.all_teams()
    assert len(teams) >= 30
    assert all(isinstance(t, ResolvedTeam) for t in teams)
