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


def _form_list(inp: AugmentInput, side: str) -> list[str]:
    return (inp.context.get(side) or {}).get("form", [])


def _injuries(inp: AugmentInput, side: str) -> list[str]:
    return (inp.context.get(side) or {}).get("injuries", [])


def template_notable(inp: AugmentInput) -> list[str]:
    """특이사항 — 데이터에 있는 사실만 (지어내지 않음)."""
    a, b = inp.team_a.display, inp.team_b.display
    out: list[str] = []
    rm = inp.recent_meeting
    if rm:
        tail = f"{rm['winner']} 승" if rm.get("winner") else "무승부"
        out.append(f"최근 맞대결: {rm['text']} ({tail})")
    if inp.elo_a and inp.elo_b and abs(inp.elo_a - inp.elo_b) >= 100:
        stronger = a if inp.elo_a > inp.elo_b else b
        out.append(f"Elo 격차가 큼(약 {round(abs(inp.elo_a - inp.elo_b))}점) — {stronger} 전력 우위 뚜렷")
    for side, name in (("a", a), ("b", b)):
        inj = _injuries(inp, side)
        if inj:
            out.append(f"{name} 부상/결장 신호 {len(inj)}건")
    return out[:4]


def template_risks(inp: AugmentInput) -> list[str]:
    """리스크 — 예측이 빗나갈 수 있는 요인 (데이터 기반)."""
    a, b = inp.team_a.display, inp.team_b.display
    out: list[str] = []
    for name, scorers in ((a, inp.scorers_a), (b, inp.scorers_b)):
        if len(scorers) >= 2 and scorers[0].p_score >= 0.30 and \
                scorers[0].p_score >= 2 * scorers[1].p_score:
            out.append(f"{name}는 득점이 {scorers[0].name}에 집중 — 봉쇄 시 공격 정체 위험")
    if inp.elo_a and inp.elo_b and abs(inp.elo_a - inp.elo_b) < 50:
        out.append("전력차가 작아 한 번의 실수로 결과가 뒤집힐 수 있음")
    for side, name in (("a", a), ("b", b)):
        fl = _form_list(inp, side)
        losses = sum(1 for f in fl if f.startswith("L"))
        if fl and losses >= 3:
            out.append(f"{name}는 최근 {len(fl)}경기 중 {losses}패로 폼이 불안정")
    if not inp.scorers_a or not inp.scorers_b:
        out.append("일부 팀 스쿼드 데이터가 부족해 득점자 예측 신뢰도가 낮음")
    return out[:4]


def template_watch_points(inp: AugmentInput) -> list[str]:
    """관전 포인트."""
    a, b = inp.team_a.display, inp.team_b.display
    o = inp.outcome
    out: list[str] = []
    if inp.scorers_a:
        out.append(f"{a}의 {inp.scorers_a[0].name}이(가) {b} 수비를 뚫을 수 있을지")
    if inp.scorers_b:
        out.append(f"{b}의 {inp.scorers_b[0].name} 견제가 승부의 관건")
    if abs(o.a_win - o.b_win) < 0.1:
        out.append("선제골과 세트피스 — 박빙 승부가 예상됨")
    else:
        fav = a if o.a_win > o.b_win else b
        out.append(f"우세한 {fav}가 기회를 살려 다득점에 성공할지")
    return out[:4]


class FallbackAugmenter:
    """통계 결과를 그대로 두고 템플릿 해설/분석 생성 (데이터 기반, 환각 없음)."""

    name = "fallback"

    def available(self) -> bool:
        return True

    def run(self, inp: AugmentInput) -> AugmentResult:
        return AugmentResult(
            scorers_a=inp.scorers_a,
            scorers_b=inp.scorers_b,
            explanation=template_explanation(inp),
            notable=template_notable(inp),
            risks=template_risks(inp),
            watch_points=template_watch_points(inp),
        )
