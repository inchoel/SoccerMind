"""FastAPI 라우트 검증 — TestClient + 가짜 service 주입 (네트워크 없음)."""

import pytest
from fastapi.testclient import TestClient

from soccermind.api.app import app
from soccermind.api.deps import get_service
from soccermind.core.models import PartialTeamData, PlayerStat, ResolvedTeam
from soccermind.core.orchestrator import PredictionService
from soccermind.data.base import DataProvider


class FakeElo(DataProvider):
    name = "elo"

    def available(self):
        return True

    def fetch(self, team: ResolvedTeam):
        ratings = {"BR": 2024.0, "KR": 1745.0}
        return PartialTeamData(source="elo", elo=ratings.get(team.elo_name))


class FakeSquad(DataProvider):
    name = "squad"

    def available(self):
        return True

    def fetch(self, team: ResolvedTeam):
        squads = {
            "BRA": [PlayerStat("Vinicius", intl_goals=10, matches=30, position="Offence")],
            "KOR": [PlayerStat("Son", intl_goals=40, matches=120, position="Offence")],
        }
        return PartialTeamData(source="squad", squad=squads.get(team.key, []))


@pytest.fixture
def client():
    svc = PredictionService(providers=[FakeElo(), FakeSquad()])  # augmenter 없음 → fallback
    app.dependency_overrides[get_service] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["providers"]["elo"] is True
    assert body["augmenter"] == "fallback"


def test_list_teams(client):
    r = client.get("/api/teams")
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) >= 30
    keys = {t["key"] for t in teams}
    assert "KOR" in keys and "BRA" in keys


def test_predict_success(client):
    r = client.get("/api/predict", params={"team_a": "브라질", "team_b": "대한민국"})
    assert r.status_code == 200
    d = r.json()
    assert d["teams"]["a"]["key"] == "BRA"
    assert d["teams"]["b"]["key"] == "KOR"
    # 확률 합 ≈ 1
    s = d["wdl"]["a_win"] + d["wdl"]["draw"] + d["wdl"]["b_win"]
    assert abs(s - 1.0) < 0.02
    # 브라질 우세
    assert d["winner"]["key"] == "BRA"
    # 스코어라인·득점자·해설 존재
    assert "a" in d["scoreline"] and "b" in d["scoreline"]
    assert any(s["name"] == "Vinicius" for s in d["scorers"]["a"])
    assert d["explanation"]


def test_predict_unknown_team_returns_400_with_candidates(client):
    r = client.get("/api/predict", params={"team_a": "Atlantis", "team_b": "브라질"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert detail["query"] == "Atlantis"
    assert isinstance(detail["candidates"], list)


def test_predict_missing_param_returns_422(client):
    r = client.get("/api/predict", params={"team_a": "브라질"})  # team_b 누락
    assert r.status_code == 422


def test_predict_korean_aliases(client):
    r = client.get("/api/predict", params={"team_a": "한국", "team_b": "brazil"})
    assert r.status_code == 200
    assert r.json()["teams"]["a"]["key"] == "KOR"


def test_tournament_endpoint(client):
    r = client.get("/api/tournament", params={"teams": "브라질,대한민국,일본,아르헨티나"})
    assert r.status_code == 200
    res = r.json()
    assert len(res) == 4
    assert abs(sum(x["prob"] for x in res) - 1.0) < 1e-3  # 4자리 반올림 오차 허용
    # 내림차순 정렬
    probs = [x["prob"] for x in res]
    assert probs == sorted(probs, reverse=True)


def test_tournament_invalid_count_returns_400(client):
    r = client.get("/api/tournament", params={"teams": "브라질,대한민국,일본"})
    assert r.status_code == 400


def test_tournament_unknown_team_returns_400(client):
    r = client.get("/api/tournament", params={"teams": "Atlantis,대한민국,일본,브라질"})
    assert r.status_code == 400
    assert r.json()["detail"]["query"] == "Atlantis"
