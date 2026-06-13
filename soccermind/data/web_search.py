"""웹검색 기반 부상/결장 속보 — LLM 해설 컨텍스트 보강 (불변식 #3: 확률 불변).

기본 비활성: 공개 레포가 무단으로 웹을 긁지 않도록 ENABLE_WEB_SEARCH 로 옵트인.
파싱(parse_ddg_results, 순수)과 검색(I/O) 분리. 검색 함수 주입으로 테스트.
참고: 아키텍처 §2(속보), 기획서 F2.
"""

from __future__ import annotations

import html as htmllib
import os
import re
from collections.abc import Callable

from ..core.models import PartialTeamData, ResolvedTeam
from .base import DataProvider
from .cache import DiskCache
from .wikipedia import team_token

DDG_URL = "https://html.duckduckgo.com/html/"
_TTL = 3600  # 속보는 1h (변동 빠름)

_SNIPPET_RE = re.compile(r"result__snippet[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)

# 부상/결장 신호 키워드 (영/한)
INJURY_KEYWORDS = (
    "injur", "ruled out", "out of", "sidelin", "doubt", "suspend", "miss the",
    "will miss", "knee", "hamstring", "부상", "결장", "징계", "출전 불투명",
)


def parse_ddg_results(html_text: str) -> list[str]:
    """DuckDuckGo HTML 결과 → 스니펫 텍스트 목록 (태그/엔티티 정리)."""
    out: list[str] = []
    for raw in _SNIPPET_RE.findall(html_text):
        text = htmllib.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
        if text:
            out.append(text)
    return out


def extract_injury_notes(snippets: list[str], limit: int = 3) -> list[str]:
    """스니펫에서 부상/결장 신호가 있는 것만 추려 최대 limit 개 (중복 제거, 길이 제한)."""
    seen: set[str] = set()
    notes: list[str] = []
    for s in snippets:
        if any(k in s.lower() for k in INJURY_KEYWORDS):
            key = s[:80]
            if key in seen:
                continue
            seen.add(key)
            notes.append(s[:200])
            if len(notes) >= limit:
                break
    return notes


def _default_search(query: str) -> list[str]:
    import httpx

    headers = {"User-Agent": "Mozilla/5.0 (SoccerMind/0.1; open-source)"}
    resp = httpx.get(DDG_URL, params={"q": query}, headers=headers, timeout=15.0)
    resp.raise_for_status()
    return parse_ddg_results(resp.text)


class WebSearchProvider(DataProvider):
    """부상/결장 속보를 웹검색으로 가져와 context['injuries'] 에 담는다 (옵트인)."""

    name = "web_search"

    def __init__(
        self,
        enabled: bool | None = None,
        search: Callable[[str], list[str]] = _default_search,
        cache: DiskCache | None = None,
    ) -> None:
        self._enabled = (
            enabled if enabled is not None else bool(os.environ.get("ENABLE_WEB_SEARCH"))
        )
        self._search = search
        self._cache = cache or DiskCache()

    def available(self) -> bool:
        return self._enabled

    def fetch(self, team: ResolvedTeam) -> PartialTeamData:
        if not self._enabled:
            return PartialTeamData(source=self.name)
        token = team_token(team.wikipedia) if team.wikipedia else team.display
        query = f"{token} national football team injury suspension squad news 2026"
        try:
            snippets = self._cache.get_or_fetch(
                f"ws:{query}", _TTL, lambda: self._search(query)
            )
        except Exception:
            return PartialTeamData(source=self.name)
        notes = extract_injury_notes(snippets)
        context = {"injuries": notes} if notes else {}
        return PartialTeamData(source=self.name, context=context)
