"""데이터 Provider 검증 — 파싱 순수성 + fetch 주입 (네트워크 없음)."""

from soccermind.core.models import ResolvedTeam
from soccermind.core.name_resolver import NameResolver
from soccermind.data.cache import DiskCache
from soccermind.data.elo_provider import EloProvider, parse_elo_tsv
from soccermind.data.football_data import FootballDataProvider, parse_squad

R = NameResolver()

# eloratings.net World.tsv 샘플 (rank, name, ..., rating 형태를 관용 파싱)
ELO_TSV = (
    "1\tSpain\t0\t2157\n"
    "2\tArgentina\t0\t2115\n"
    "3\tFrance\t-1\t2063\n"
    "5\tBrazil\t2\t2024\n"
    "23\tKorea South\t1\t1745\n"
    "\n"  # 빈 줄 무시
)


def test_parse_elo_tsv():
    ratings = parse_elo_tsv(ELO_TSV)
    assert ratings["Spain"] == 2157.0
    assert ratings["Korea South"] == 1745.0
    assert "France" in ratings
    assert len(ratings) == 5  # 빈 줄 제외


def test_parse_elo_ignores_rank_as_rating():
    # rank(1,2,..)는 레이팅(1000~2500)으로 오인되면 안 됨
    ratings = parse_elo_tsv("1\tSpain\t0\t2157\n")
    assert ratings == {"Spain": 2157.0}


def test_elo_provider_fetch_uses_injected_text(tmp_path):
    calls = {"n": 0}

    def fake_fetch(url):
        calls["n"] += 1
        return ELO_TSV

    prov = EloProvider(fetch_text=fake_fetch, cache=DiskCache(tmp_path))
    assert prov.available() is True

    kor = R.resolve("대한민국")
    partial = prov.fetch(kor)
    assert partial.source == "elo"
    assert partial.elo == 1745.0

    # 캐시 적중으로 두 번째 호출은 네트워크 미사용
    prov.fetch(R.resolve("브라질"))
    assert calls["n"] == 1


def test_elo_provider_unknown_team_returns_none_elo(tmp_path):
    prov = EloProvider(fetch_text=lambda url: ELO_TSV, cache=DiskCache(tmp_path))
    # elo_name 이 TSV 에 없는 팀
    ghana = R.resolve("가나")
    assert prov.fetch(ghana).elo is None


# football-data.org team 리소스 샘플
TEAM_JSON = {
    "id": 770,
    "name": "South Korea",
    "squad": [
        {"name": "Son Heung-min", "position": "Offence"},
        {"name": "Kim Min-jae", "position": "Defence"},
        {"name": "Jo Hyeon-woo", "position": "Goalkeeper"},
        {"name": "Lee Kang-in", "position": "Midfield"},
    ],
}


def test_parse_squad():
    squad = parse_squad(TEAM_JSON)
    assert len(squad) == 4
    names = {p.name for p in squad}
    assert "Son Heung-min" in names
    gk = next(p for p in squad if p.name == "Jo Hyeon-woo")
    assert gk.is_goalkeeper is True


def test_parse_squad_empty():
    assert parse_squad({}) == []
    assert parse_squad({"squad": None}) == []


def test_football_data_unavailable_without_token():
    prov = FootballDataProvider(token="")
    assert prov.available() is False
    # 토큰 없으면 빈 데이터 (예외 아님)
    partial = prov.fetch(R.resolve("대한민국"))
    assert partial.squad == []


def test_football_data_fetch_with_injected_json(tmp_path):
    # fd_id 는 aliases 에 검증된 값만 들어가므로, 테스트는 명시적 ResolvedTeam 사용
    team = ResolvedTeam(key="KOR", display="대한민국", fd_id=770)

    def fake_json(url, token):
        assert "770" in url
        assert token == "TESTKEY"
        return TEAM_JSON

    prov = FootballDataProvider(
        token="TESTKEY", fetch_json=fake_json, cache=DiskCache(tmp_path)
    )
    assert prov.available() is True
    partial = prov.fetch(team)
    assert partial.source == "football_data"
    assert len(partial.squad) == 4


def test_football_data_no_fd_id_returns_empty(tmp_path):
    # fd_id 가 없는 팀(예: 북한)은 빈 데이터
    prov = FootballDataProvider(token="TESTKEY", fetch_json=lambda u, t: TEAM_JSON,
                                cache=DiskCache(tmp_path))
    partial = prov.fetch(R.resolve("북한"))
    assert partial.squad == []
