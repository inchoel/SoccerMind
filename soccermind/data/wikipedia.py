"""Wikipedia (MediaWiki API) 스쿼드 — 키 불필요, 전 팀 커버 (스쿼드 폴백).

국가대표 문서의 위키텍스트에서 {{nat fs player}} 템플릿을 파싱해 이름·포지션과
가능하면 통산 득점(goals)·출전(caps)까지 추출. 파싱(순수)과 fetch(I/O) 분리.
참고: 아키텍처 §2(보강), 기획서 F2.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from ..core.models import PartialTeamData, PlayerStat, ResolvedTeam
from .base import DataProvider
from .cache import DiskCache

WIKI_API = "https://en.wikipedia.org/w/api.php"
_TTL = 24 * 3600

_POS_MAP = {"GK": "Goalkeeper", "DF": "Defence", "MF": "Midfield", "FW": "Offence"}
# 스쿼드 선수 템플릿 변형: {{nat fs player}}, {{nat fs g player}}(포지션 그룹형)
_PLAYER_TEMPLATES = ("nat fs g player", "nat fs player")
_SCORE_RE = re.compile(r"(\d+)\s*[–—-]\s*(\d+)")
_TITLE_SUFFIXES = (
    " national football team",
    " men's national soccer team",
    " national association football team",
)


def _param(block: str, key: str) -> str:
    # 값은 다음 파라미터(|word=) 또는 블록 끝까지 — 위키링크 내부 '|' 에 끊기지 않도록
    m = re.search(
        rf"\|\s*{key}\s*=\s*(.*?)(?=\s*\|\s*[\w-]+\s*=|$)",
        block,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(1).strip() if m else ""


def _clean_name(raw: str) -> str:
    # [[A|B]] → B, [[A]] → A, 굵게/기울임 마크업 제거
    raw = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", raw)
    return raw.replace("'''", "").replace("''", "").strip()


def parse_squad_from_wikitext(text: str) -> list[PlayerStat]:
    """위키텍스트 → PlayerStat 목록. goals/caps 있으면 득점 가중에 활용.

    {{nat fs player}}·{{nat fs g player}} 모두 지원. 중첩 템플릿(예: {{birth date and age}})
    때문에 중괄호 균형 추출기(_find_templates)를 사용 — 단순 정규식은 중첩 }} 에서 잘린다.
    """
    out: list[PlayerStat] = []
    blocks: list[str] = []
    for tmpl in _PLAYER_TEMPLATES:
        blocks.extend(_find_templates(text, tmpl))
    for block in blocks:
        name = _clean_name(_param(block, "name"))
        if not name:
            continue
        pos = _param(block, "pos").upper()
        goals = _param(block, "goals")
        caps = _param(block, "caps")
        out.append(
            PlayerStat(
                name=name,
                position=_POS_MAP.get(pos, pos),
                intl_goals=int(goals) if goals.isdigit() else 0,
                matches=int(caps) if caps.isdigit() else 0,
                is_pen_taker=False,
            )
        )
    return out


def _strip_markup(s: str) -> str:
    """플래그아이콘 등 템플릿/링크/굵게 마크업 제거 → 표시 텍스트."""
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)  # 단순 템플릿(flagicon 등)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)  # 위키링크
    return s.replace("'''", "").replace("''", "").strip()


def team_token(wikipedia_title: str) -> str:
    """문서 제목에서 국가명 토큰 추출 ('South Korea national football team' → 'South Korea')."""
    for suf in _TITLE_SUFFIXES:
        if wikipedia_title.endswith(suf):
            return wikipedia_title[: -len(suf)]
    return wikipedia_title


def _find_templates(text: str, name: str) -> list[str]:
    """{{name ...}} 템플릿들의 내부 내용을 추출 (중첩 중괄호 인식).

    각 템플릿 '시작'을 정규식으로 직접 찾고 그 지점부터 지역 중괄호 균형 스캔으로
    끝을 찾는다 → 문서 다른 곳의 불균형 중괄호(큰 인포박스 등)에 영향받지 않음.
    이름 뒤 경계(|/})로 'Football box' 가 'Football box collapsible' 을 매칭하지 않게 함.
    """
    blocks: list[str] = []
    n = len(text)
    last_end = 0
    start_re = re.compile(r"\{\{\s*" + re.escape(name) + r"\s*(?=[|}])", re.IGNORECASE)
    for m in start_re.finditer(text):
        s = m.start()
        if s < last_end:  # 앞 템플릿 내부에 중첩된 동명 시작은 건너뜀
            continue
        depth, k = 0, s
        while k < n:
            if text.startswith("{{", k):
                depth += 1
                k += 2
            elif text.startswith("}}", k):
                depth -= 1
                k += 2
                if depth == 0:
                    break
            else:
                k += 1
        blocks.append(text[s + 2 : k - 2])
        last_end = k
    return blocks


def parse_recent_form(wikitext: str, token: str, limit: int = 5) -> list[str]:
    """Football box 결과에서 토큰 팀의 최근 폼(가장 최근 우선) ['L 1-3 vs Spain', ...]."""
    forms: list[str] = []
    for block in _find_templates(wikitext, "Football box collapsible") + _find_templates(
        wikitext, "Football box"
    ):
        m = _SCORE_RE.search(_param(block, "score"))
        if not m:
            continue
        t1 = _strip_markup(_param(block, "team1"))
        t2 = _strip_markup(_param(block, "team2"))
        g1, g2 = int(m.group(1)), int(m.group(2))
        tl = token.lower()
        if tl in t1.lower():
            gf, ga, opp = g1, g2, t2
        elif tl in t2.lower():
            gf, ga, opp = g2, g1, t1
        else:
            continue
        res = "W" if gf > ga else ("D" if gf == ga else "L")
        forms.append(f"{res} {gf}-{ga} vs {opp}")
    # 문서상 보통 시간 오름차순 → 뒤쪽이 최근. 최근 N 을 최신순으로.
    return forms[-limit:][::-1]


def _default_fetch_wikitext(title: str) -> str:
    import httpx

    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
    }
    # Wikimedia UA 정책: 연락처 URL 필수 (없으면 403). GitHub 레포 URL 로 식별.
    headers = {
        "User-Agent": "SoccerMind/0.1 (https://github.com/inchoel/SoccerMind)",
        "Accept": "application/json",
    }
    resp = httpx.get(WIKI_API, params=params, headers=headers, timeout=15.0)
    resp.raise_for_status()
    return resp.json().get("parse", {}).get("wikitext", "")


class WikipediaProvider(DataProvider):
    """국가대표 스쿼드를 Wikipedia 에서 가져온다 (키 불필요 → 항상 available)."""

    name = "wikipedia"

    def __init__(
        self,
        fetch_wikitext: Callable[[str], str] = _default_fetch_wikitext,
        cache: DiskCache | None = None,
    ) -> None:
        self._fetch_wikitext = fetch_wikitext
        self._cache = cache or DiskCache()

    def available(self) -> bool:
        return True

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        if not team.wikipedia:
            return PartialTeamData(source=self.name)
        try:
            text = self._cache.get_or_fetch(
                f"wiki:{team.wikipedia}", _TTL, lambda: self._fetch_wikitext(team.wikipedia)
            )
        except Exception:
            return PartialTeamData(source=self.name)
        form = parse_recent_form(text, team_token(team.wikipedia))
        context = {"form": form} if form else {}
        return PartialTeamData(
            source=self.name, squad=parse_squad_from_wikitext(text), context=context
        )
