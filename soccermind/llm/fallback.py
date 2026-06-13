"""LLM 키 부재 시 폴백 — 통계 랭킹 유지 + 템플릿 해설 (graceful degradation, 불변식 #5)."""

from __future__ import annotations

from .base import AugmentInput, AugmentResult


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def template_explanation(inp: AugmentInput) -> str:
    a, b = inp.team_a.display, inp.team_b.display
    o = inp.outcome
    x, y, p = inp.scoreline

    best = max(o.a_win, o.draw, o.b_win)
    if best == o.draw:
        head = f"{a}와(과) {b}는 박빙으로, 무승부 가능성이 {_pct(o.draw)}로 가장 높습니다."
    else:
        winner, conf = (a, o.a_win) if o.a_win > o.b_win else (b, o.b_win)
        head = f"{winner}이(가) {_pct(conf)} 우세로 승리가 예상됩니다."

    line = f" 가장 가능성 높은 스코어는 {x}-{y} ({_pct(p)})입니다."

    def scorer_str(scorers):
        top = scorers[:3]
        return ", ".join(f"{s.name}({_pct(s.p_score)})" for s in top) if top else "정보 없음"

    scorers = (
        f" 주요 득점 후보 — {a}: {scorer_str(inp.scorers_a)};"
        f" {b}: {scorer_str(inp.scorers_b)}."
    )
    return head + line + scorers


class FallbackAugmenter:
    """통계 결과를 그대로 두고 템플릿 해설만 생성."""

    name = "fallback"

    def available(self) -> bool:
        return True

    def run(self, inp: AugmentInput) -> AugmentResult:
        return AugmentResult(
            scorers_a=inp.scorers_a,
            scorers_b=inp.scorers_b,
            explanation=template_explanation(inp),
        )
