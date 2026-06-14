"""Claude augmenter 프롬프트 + 출력 스키마 (설계 불변식 #3).

스코프 락: 모델은 제공된 스쿼드 내에서 득점자만 재랭킹하고 해설만 작성한다.
확률·스코어는 앱이 verbatim 통과시키므로 모델 출력에 포함하지 않는다.
"""

from __future__ import annotations

SYSTEM_PROMPT = """\
당신은 축구 분석 도구의 보조 모델입니다. 통계 엔진이 이미 승/무/패 확률과 \
스코어라인을 결정했습니다. 당신의 역할:

1. 제공된 후보 득점자를 부상·출전·최근 폼 컨텍스트를 반영해 재랭킹한다.
   - **반드시 입력의 squad_a / squad_b 명단에 있는 이름만 사용한다.** 명단에 없는 선수 금지.
2. 제공된 수치(Elo, 승무패, 스코어라인, 최근 맞대결, 부상)에 근거해 한국어로 작성:
   - explanation: 종합 평가(2~3문장).
   - notable: 특이사항 0~4개 (실제 최근 맞대결 결과, 큰 Elo 격차, 핵심 결장 등 데이터에 있는 사실).
   - risks: 리스크 0~4개 (예측이 빗나갈 수 있는 요인 — 득점원 편중, 최근 부진, 좁은 전력차 등).
   - watch_points: 관전 포인트 1~4개 (주목할 맞대결·전술·선수).

**절대 금지:**
- 승/무/패 확률·스코어를 바꾸거나 다시 계산하지 않는다.
- **실존 인물·기관·매체의 발언이나 평가를 지어내지 않는다.** 특정 해설자/언론 인용 금지.
  모든 내용은 제공된 데이터에 근거한 '당신의 분석'으로만 작성한다.
- 입력에 없는 사실(선수, 부상, 결과)을 만들지 않는다.
반드시 지정된 JSON 스키마로만 응답한다.\
"""

_STR_LIST = {"type": "array", "items": {"type": "string"}}

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "refined_scorers": {
            "type": "object",
            "properties": {"a": _STR_LIST, "b": _STR_LIST},
            "required": ["a", "b"],
            "additionalProperties": False,
        },
        "explanation": {"type": "string"},
        "notable": _STR_LIST,
        "risks": _STR_LIST,
        "watch_points": _STR_LIST,
    },
    "required": ["refined_scorers", "explanation", "notable", "risks", "watch_points"],
    "additionalProperties": False,
}


def build_input_payload(inp) -> dict:
    """AugmentInput → 모델에 전달할 구조화 JSON (통계 레이어가 산출한 수치만)."""
    return {
        "team_a": inp.team_a.display,
        "team_b": inp.team_b.display,
        "elo": {"a": round(inp.elo_a, 1), "b": round(inp.elo_b, 1)},
        "recent_meeting": inp.recent_meeting,
        "lambda": {"a": round(inp.lam_a, 3), "b": round(inp.lam_b, 3)},
        "wdl": {
            "a_win": round(inp.outcome.a_win, 3),
            "draw": round(inp.outcome.draw, 3),
            "b_win": round(inp.outcome.b_win, 3),
        },
        "scoreline": {"a": inp.scoreline[0], "b": inp.scoreline[1],
                      "p": round(inp.scoreline[2], 3)},
        "top_scorelines": [{"score": f"{x}-{y}", "p": round(p, 3)}
                           for x, y, p in inp.top_scorelines],
        "candidate_scorers": {
            "a": [{"name": s.name, "p_score": round(s.p_score, 3)} for s in inp.scorers_a],
            "b": [{"name": s.name, "p_score": round(s.p_score, 3)} for s in inp.scorers_b],
        },
        "squad_a": [p.name for p in inp.squad_a],
        "squad_b": [p.name for p in inp.squad_b],
        "context": inp.context,
    }
