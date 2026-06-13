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

_PLAYER_RE = re.compile(r"\{\{\s*nat fs player(.*?)\}\}", re.IGNORECASE | re.DOTALL)
_POS_MAP = {"GK": "Goalkeeper", "DF": "Defence", "MF": "Midfield", "FW": "Offence"}


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
    """위키텍스트 → PlayerStat 목록. goals/caps 있으면 득점 가중에 활용."""
    out: list[PlayerStat] = []
    for block in _PLAYER_RE.findall(text):
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
    headers = {"User-Agent": "SoccerMind/0.1 (open-source predictor; contact via GitHub)"}
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
        return PartialTeamData(source=self.name, squad=parse_squad_from_wikitext(text))
