"""API 라우트 — /api/predict, /api/teams, /healthz."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..core.orchestrator import PredictOptions, PredictionService, ResolutionError
from .deps import get_service
from .schemas import ChampionOut, PredictionResponse, TeamListItem, to_response

router = APIRouter()


@router.get("/healthz")
def healthz(svc: PredictionService = Depends(get_service)) -> dict:
    """헬스 체크 + 각 provider/augmenter 가용 상태."""
    providers = {p.name: p.available() for p in svc.providers}
    augmenter = svc.augmenter.name if (svc.augmenter and svc.augmenter.available()) else "fallback"
    return {"status": "ok", "providers": providers, "augmenter": augmenter}


@router.get("/api/teams", response_model=list[TeamListItem])
def list_teams(svc: PredictionService = Depends(get_service)) -> list[TeamListItem]:
    """지원 국가 목록 (UI 자동완성용)."""
    return [TeamListItem(key=t.key, name=t.display) for t in svc.resolver.all_teams()]


@router.get("/api/predict", response_model=PredictionResponse)
def predict(
    team_a: str = Query(..., description="첫 번째 국가명 (한/영)"),
    team_b: str = Query(..., description="두 번째 국가명 (한/영)"),
    host: str | None = Query(None, description="개최국 표준키 (선택, 예: BRA)"),
    previews: bool = Query(False, description="전문가 프리뷰(웹검색) 표시 — 고객 선택"),
    svc: PredictionService = Depends(get_service),
) -> PredictionResponse:
    try:
        pred = svc.predict(team_a, team_b, PredictOptions(host_key=host, want_previews=previews))
    except ResolutionError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": str(e),
                "query": e.query,
                "candidates": [{"key": c.key, "name": c.display} for c in e.candidates],
            },
        ) from e
    return to_response(pred)


@router.get("/api/tournament", response_model=list[ChampionOut])
def tournament(
    teams: str = Query(..., description="쉼표로 구분한 국가명(2의 거듭제곱), 시드 순"),
    svc: PredictionService = Depends(get_service),
) -> list[ChampionOut]:
    names = [t.strip() for t in teams.split(",") if t.strip()]
    try:
        result = svc.tournament(names)
    except ResolutionError as e:
        raise HTTPException(
            status_code=400,
            detail={"detail": str(e), "query": e.query,
                    "candidates": [{"key": c.key, "name": c.display} for c in e.candidates]},
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"detail": str(e)}) from e
    return [ChampionOut(name=n, prob=round(p, 4)) for n, p in result]
