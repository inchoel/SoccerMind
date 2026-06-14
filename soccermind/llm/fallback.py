"""LLM 키 부재 시 폴백 — 통계 랭킹 유지 + 템플릿 해설 (graceful degradation, 불변식 #5)."""

from __future__ import annotations

from .base import AugmentInput, AugmentResult


def _pct(x: float) -> str:
    return f"{round(x * 100)}%"


def template_explanation(inp: AugmentInput) -> str:
    """근거 데이터(Elo·최근 폼·실제 맞대결)를 곁들인 한국어 해설."""
    a, b = inp.team_a.display, inp.team_b.display
    o = inp.outcome
    x, y, p = inp.scoreline

    best = max(o.a_win, o.draw, o.b_win)
    if best == o.draw:
        head = f"{a}와(과) {b}는 전력이 비슷해 무승부 가능성이 {_pct(o.draw)}로 가장 높습니다."
    else:
        winner, conf = (a, o.a_win) if o.a_win > o.b_win else (b, o.b_win)
        head = f"{winner}이(가) {_pct(conf)} 우세로 승리가 예상됩니다."

    # 근거: Elo 격차
    basis = ""
    if inp.elo_a and inp.elo_b:
        gap = abs(inp.elo_a - inp.elo_b)
        stronger = a if inp.elo_a >= inp.elo_b else b
        if gap >= 20:
            basis = f" Elo 레이팅은 {a} {round(inp.elo_a)} 대 {b} {round(inp.elo_b)}로 {stronger}이(가) 앞섭니다."
        else:
            basis = f" Elo 레이팅({a} {round(inp.elo_a)} · {b} {round(inp.elo_b)})은 거의 호각입니다."

    line = f" 통계 모델 기준 가장 유력한 스코어는 {x}-{y}입니다."

    # 근거: 실제 최근 맞대결 (이미 치러진 경기)
    meeting = ""
    if inp.recent_meeting:
        rm = inp.recent_meeting
        if rm.get("winner"):
            meeting = f" 참고로 최근 맞대결에서는 {rm['text']}로 {rm['winner']}이(가) 승리했습니다."
        else:
            meeting = f" 참고로 최근 맞대결은 {rm['text']} 무승부였습니다."

    def scorer_str(scorers):
        top = scorers[:3]
        return ", ".join(f"{s.name}({_pct(s.p_score)})" for s in top) if top else "정보 없음"

    scorers = (
        f" 주요 득점 후보는 {a} {scorer_str(inp.scorers_a)},"
        f" {b} {scorer_str(inp.scorers_b)}입니다."
    )
    return head + basis + line + meeting + scorers


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
