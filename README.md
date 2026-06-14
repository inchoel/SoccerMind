# SoccerMind ⚽🧠

[![CI](https://github.com/inchoel/SoccerMind/actions/workflows/ci.yml/badge.svg)](https://github.com/inchoel/SoccerMind/actions/workflows/ci.yml)

두 국가명을 입력받아 **승리 국가 · 예상 스코어 · 예상 득점자**를 예측하는, 실시간 데이터 기반 오픈소스 분석 도구.

> 재미용 룰렛이 아니라 **실제 공개 데이터 + 검증된 통계 모델 + LLM 보강**으로 재현 가능하고 설명 가능한 예측을 제공합니다.

## 주요 기능

| 기능 | 설명 |
|------|------|
| ⚽ **경기 예측** | 두 국가 → 승리국·예상 스코어·득점자·자연어 해설 (한·영 국가명, 임의 대진 지원) |
| 🏆 **토너먼트 우승확률** | 참가국(2ⁿ) → 정확한 브래킷 DP로 우승 확률 랭킹 |
| 📊 **승/무/패 분포** | 스코어 매트릭스에서 산출한 확률 + 상위 스코어라인 |
| 🎯 **득점자 예측** | 선수별 기대득점(xG) → 득점 확률 랭킹 (골키퍼 제외) |
| 📈 **최근 폼** | Wikipedia 결과에서 팀별 최근 W/D/L |
| 🩹 **부상/결장 속보** | 웹검색 기반 LLM 컨텍스트 보강 (옵트인) |
| 🔧 **모델 보정** | 과거 경기 Elo replay → β1·ρ 피팅 → 영속화 (백테스트 RPS/Brier) |
| 🌐 **웹 UI + REST API** | FastAPI + 정적 SPA (두 탭) |

## 예측 방식 (하이브리드)

```
Elo 레이팅 ──► 기대득점(λ) ──► 스코어 매트릭스(Dixon-Coles)  ← 유일한 진실의 원천
                                     │
              ┌──────────────────────┼─────────────────────┐
              ▼                      ▼                     ▼
          승/무/패 확률          최빈 스코어라인         선수별 xG → 득점자
                                                         (LLM이 재랭킹·해설)
```

- **통계 레이어**가 모든 확률·스코어를 결정적으로 산출 (동일 입력 → 동일 출력).
- **LLM 레이어**는 득점자 재랭킹과 자연어 해설만 담당하며 확률은 변경하지 못함 (스키마 제약 + 스쿼드 검증 가드레일).

## 데이터 소스

| 소스 | 용도 | 키 | 비고 |
|------|------|----|------|
| eloratings.net | 팀 강도(Elo) | 불필요 | 모델 강도 입력 |
| Wikipedia (MediaWiki) | 스쿼드·최근 폼 | 불필요 | 전 팀 커버 |
| API-Football | 선수 득점 통계 | 무료 자가발급 | 득점자 품질↑ (선택) |
| football-data.org | WC 경기·스쿼드 | 무료 자가발급 | 백본 (선택) |
| 웹검색(DuckDuckGo) | 부상/결장 속보 | 불필요 | `ENABLE_WEB_SEARCH` 옵트인 |

여러 소스를 우선순위로 **병합**하며, 키가 없는 소스는 자동 스킵됩니다.

### Graceful degradation

| 보유 키 | 동작 |
|---------|------|
| **없음** | Elo 예측 + Wikipedia 스쿼드/폼 + 템플릿 해설 (동작 보장) |
| `+ ANTHROPIC_API_KEY` | 위 + LLM 득점자 재랭킹·해설 |
| `+ API_FOOTBALL_KEY` | 위 + 선수 득점 통계로 득점자 가중 |
| `+ FOOTBALL_DATA_TOKEN` | 위 + WC 경기/스쿼드 백본, 과거경기 보정 입력 |
| `ENABLE_WEB_SEARCH=1` | 위 + 부상/결장 속보 컨텍스트 |

## 빠른 시작

```bash
python -m venv .venv && .venv\Scripts\activate        # Windows (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"                                # LLM 포함: ".[dev,llm]"
cp .env.example .env                                   # 본인 키 입력 (없어도 동작)
uvicorn soccermind.api.app:app --reload                # → http://127.0.0.1:8000
pytest -q                                              # 테스트 (현재 148 passed)
```

브라우저에서 **경기 예측**과 **토너먼트 우승** 두 탭을 사용할 수 있습니다.

## API & 명령어

| 종류 | 예시 |
|------|------|
| 경기 예측 | `GET /api/predict?team_a=대한민국&team_b=브라질` |
| 토너먼트 | `GET /api/tournament?teams=브라질,아르헨티나,프랑스,스페인` (2ⁿ) |
| 지원 국가 | `GET /api/teams` |
| 헬스체크 | `GET /healthz` (provider/augmenter 가용 상태) |
| 모델 보정 | `python -m soccermind.calibrate WC` (과거경기 replay→fit→저장) |

## 문서

- [기획서 (PRD)](./docs/기획서.md)
- [아키텍처 설계](./docs/아키텍처.md)

## 상태

✅ 통계 엔진(Elo→스코어매트릭스) · 국가명 정규화 · 데이터 레이어(5종 소스 + TTL 캐시) · 오케스트레이터 · LLM augmenter(가드레일) · 모델 보정/백테스트 · 토너먼트 DP · FastAPI/웹 UI. Python 3.11+ · CI(ruff + pytest, 3.11–3.13).

## 라이선스

MIT (예정)
