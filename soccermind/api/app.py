"""FastAPI 앱 — 라우트 + 정적 웹 UI 마운트."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import routes

app = FastAPI(
    title="SoccerMind",
    description="두 국가명 → 승리국·스코어·득점자 예측",
    version="0.1.0",
)

# API 라우트를 먼저 등록 (정적 마운트보다 우선 매칭)
app.include_router(routes.router)

# 정적 웹 UI 를 루트에 마운트 (html=True → index.html 서빙)
_web_dir = Path(__file__).resolve().parent.parent.parent / "web"
if _web_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_web_dir), html=True), name="web")
