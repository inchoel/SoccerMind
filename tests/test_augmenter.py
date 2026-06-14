"""ClaudeAugmenter 검증 — 가짜 client 주입, 네트워크 없음 (불변식 #3)."""

import json
import types

from soccermind.core.models import PlayerStat, ResolvedTeam, ScorerProb
from soccermind.engine.score_matrix import Outcome
from soccermind.llm.augmenter import ClaudeAugmenter
from soccermind.llm.base import AugmentInput


def _input():
    return AugmentInput(
        team_a=ResolvedTeam("BRA", "브라질"),
        team_b=ResolvedTeam("KOR", "대한민국"),
        lam_a=1.9, lam_b=1.0,
        outcome=Outcome(a_win=0.61, draw=0.18, b_win=0.21),
        scoreline=(2, 1, 0.11),
        top_scorelines=[(2, 1, 0.11)],
        scorers_a=[ScorerProb("Vinicius", 0.5, 0.39), ScorerProb("Rodrygo", 0.3, 0.26)],
        scorers_b=[ScorerProb("Son", 0.4, 0.33)],
        squad_a=[PlayerStat("Vinicius"), PlayerStat("Rodrygo"), PlayerStat("Raphinha")],
        squad_b=[PlayerStat("Son"), PlayerStat("Lee")],
    )


class FakeClient:
    """messages.create 가 미리 정한 JSON 텍스트를 반환하는 가짜 Anthropic client."""

    def __init__(self, payload: dict | None = None, raise_exc: Exception | None = None):
        self._payload = payload
        self._raise = raise_exc
        self.calls = []

        outer = self

        class _Messages:
            def create(self, **kwargs):
                outer.calls.append(kwargs)
                if outer._raise:
                    raise outer._raise
                text = json.dumps(outer._payload, ensure_ascii=False)
                block = types.SimpleNamespace(type="text", text=text)
                return types.SimpleNamespace(content=[block])

        self.messages = _Messages()


def test_available_true_when_client_injected():
    assert ClaudeAugmenter(client=FakeClient({})).available() is True


def test_available_false_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # client 미주입 + 키 없음 → 사용 불가
    assert ClaudeAugmenter().available() is False


def test_run_reranks_valid_scorers():
    payload = {
        "refined_scorers": {"a": ["Rodrygo", "Vinicius"], "b": ["Son"]},
        "explanation": "브라질 우세, 호드리구가 폼이 좋아 1순위.",
    }
    aug = ClaudeAugmenter(client=FakeClient(payload))
    result = aug.run(_input())
    # LLM 순서대로 재정렬, baseline 확률 유지
    assert [s.name for s in result.scorers_a] == ["Rodrygo", "Vinicius"]
    assert result.scorers_a[0].p_score == 0.26  # Rodrygo 의 baseline 확률
    assert result.explanation.startswith("브라질")


def test_run_rejects_hallucinated_name_falls_back():
    # 스쿼드에 없는 'Messi' → 가드레일이 통계 랭킹으로 폴백 (A팀만)
    payload = {
        "refined_scorers": {"a": ["Messi", "Vinicius"], "b": ["Son"]},
        "explanation": "...",
    }
    aug = ClaudeAugmenter(client=FakeClient(payload))
    result = aug.run(_input())
    # A팀은 통계 랭킹 그대로 (환각 거부)
    assert [s.name for s in result.scorers_a] == ["Vinicius", "Rodrygo"]
    # B팀은 유효하므로 LLM 결과 사용
    assert [s.name for s in result.scorers_b] == ["Son"]


def test_run_api_error_falls_back_to_template():
    aug = ClaudeAugmenter(client=FakeClient(raise_exc=RuntimeError("API down")))
    result = aug.run(_input())
    # 통계 랭킹 유지 + 템플릿 해설
    assert [s.name for s in result.scorers_a] == ["Vinicius", "Rodrygo"]
    assert "브라질" in result.explanation
    assert "2-1" in result.explanation


def test_run_uses_structured_output_and_model():
    payload = {"refined_scorers": {"a": ["Vinicius"], "b": ["Son"]}, "explanation": "x"}
    fake = FakeClient(payload)
    ClaudeAugmenter(client=fake).run(_input())
    kwargs = fake.calls[0]
    assert kwargs["model"] == "claude-opus-4-8"
    # 구조화 출력(JSON 스키마) 사용 확인
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    # temperature 미전달 (Opus 4.8 미지원)
    assert "temperature" not in kwargs


def test_orchestrator_uses_claude_when_available():
    # 오케스트레이터가 available augmenter 를 우선 사용하는지
    from soccermind.core.models import PartialTeamData
    from soccermind.core.orchestrator import PredictionService
    from soccermind.data.base import DataProvider

    class FakeElo(DataProvider):
        name = "elo"

        def available(self):
            return True

        def fetch(self, team):
            ratings = {"BR": 2024.0, "KR": 1745.0}
            return PartialTeamData(source="elo", elo=ratings.get(team.elo_name))

    payload = {"refined_scorers": {"a": [], "b": []}, "explanation": "클로드 해설"}
    aug = ClaudeAugmenter(client=FakeClient(payload))
    svc = PredictionService(providers=[FakeElo()], augmenter=aug)
    pred = svc.predict("브라질", "대한민국")
    assert pred.meta["augmenter"] == "claude"
    assert pred.explanation == "클로드 해설"
