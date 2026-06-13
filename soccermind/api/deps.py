"""FastAPI 의존성 — PredictionService 싱글턴 (테스트는 dependency_overrides 로 교체)."""

from __future__ import annotations

from ..config.settings import build_service
from ..core.orchestrator import PredictionService

_service: PredictionService | None = None


def get_service() -> PredictionService:
    global _service
    if _service is None:
        _service = build_service()
    return _service
