"""결과 파서/provider 검증 — 종료 경기 필터 + 시간순."""

from soccermind.data.cache import DiskCache
from soccermind.data.results_provider import ResultsProvider, parse_finished_matches

JSON = {
    "matches": [
        {"status": "FINISHED", "utcDate": "2026-06-12T18:00:00Z",
         "homeTeam": {"name": "Brazil"}, "awayTeam": {"name": "Korea Republic"},
         "score": {"fullTime": {"home": 2, "away": 1}}},
        {"status": "FINISHED", "utcDate": "2026-06-10T18:00:00Z",
         "homeTeam": {"name": "Japan"}, "awayTeam": {"name": "Spain"},
         "score": {"fullTime": {"home": 0, "away": 0}}},
        {"status": "SCHEDULED", "utcDate": "2026-06-20T18:00:00Z",
         "homeTeam": {"name": "X"}, "awayTeam": {"name": "Y"},
         "score": {"fullTime": {"home": None, "away": None}}},
        {"status": "FINISHED", "utcDate": "2026-06-11T18:00:00Z",
         "homeTeam": {"name": "A"}, "awayTeam": {"name": "B"},
         "score": {"fullTime": {"home": None, "away": None}}},  # 스코어 없음 → 제외
    ]
}


def test_parse_filters_and_sorts():
    rows = parse_finished_matches(JSON)
    assert len(rows) == 2  # FINISHED + 스코어 있는 것만
    # 시간순 정렬 (Japan 06-10 → Brazil 06-12)
    assert rows[0].team_a == "Japan"
    assert rows[1].team_a == "Brazil"
    assert rows[1].goals_a == 2 and rows[1].goals_b == 1


def test_parse_empty():
    assert parse_finished_matches({}) == []
    assert parse_finished_matches({"matches": None}) == []


def test_provider_unavailable_without_token():
    p = ResultsProvider(token="")
    assert p.available() is False
    assert p.fetch_competition("WC") == []


def test_provider_fetch_with_injected_json(tmp_path):
    def fake_json(url, token):
        assert "WC" in url and token == "TESTKEY"
        return JSON

    p = ResultsProvider(token="TESTKEY", fetch_json=fake_json, cache=DiskCache(tmp_path))
    rows = p.fetch_competition("WC")
    assert len(rows) == 2
