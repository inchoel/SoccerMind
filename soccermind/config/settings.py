"""서비스 조립 — 환경변수(.env)로 provider/augmenter 구성 (graceful degradation)."""

from __future__ import annotations

from ..core.orchestrator import PredictionService
from ..data.api_football import ApiFootballProvider
from ..data.cache import DiskCache
from ..data.elo_provider import EloProvider
from ..data.football_data import FootballDataProvider
from ..data.web_search import WebSearchProvider
from ..data.wikipedia import WikipediaProvider
from ..engine.config import CONFIG_PATH, load_config
from ..llm.augmenter import ClaudeAugmenter


def load_dotenv_if_present() -> None:
    """.env 가 있으면 로드 (python-dotenv). 없거나 미설치면 조용히 통과."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def build_service(
    cache: DiskCache | None = None, config_path: str = CONFIG_PATH
) -> PredictionService:
    """기본 provider/augmenter + 보정된 상수로 PredictionService 구성.

    키가 없는 provider/augmenter 는 available()=False 로 자동 스킵된다.
    보정 상수 파일(config_path)이 있으면 로드해 예측에 반영, 없으면 기본값.
    """
    load_dotenv_if_present()
    cache = cache or DiskCache()
    cfg = load_config(config_path)  # 보정 결과 반영 (없으면 DEFAULT_CONFIG)
    providers = [
        EloProvider(cache=cache),  # 키 불필요 (Elo)
        # API-Football 을 football-data 보다 먼저 → 득점 통계 있는 스쿼드가 병합 우선
        ApiFootballProvider(cache=cache),  # API_FOOTBALL_KEY 있으면 활성 (선수 득점 통계)
        FootballDataProvider(cache=cache),  # FOOTBALL_DATA_TOKEN 있으면 활성 (스쿼드)
        WikipediaProvider(cache=cache),  # 키 불필요 — 전 팀 스쿼드 최종 폴백
        WebSearchProvider(cache=cache),  # ENABLE_WEB_SEARCH 옵트인 — 부상/결장 속보
    ]
    augmenter = ClaudeAugmenter()  # ANTHROPIC_API_KEY 있으면 활성
    return PredictionService(providers=providers, augmenter=augmenter, cfg=cfg)
