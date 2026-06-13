# CLAUDE.md

SoccerMind — 두 국가명 입력 → **승리국·스코어·득점자** 예측하는 실시간 데이터 기반 오픈소스 분석 도구. Python 3.11+ / FastAPI 웹앱.

## 먼저 읽을 문서 (진실의 원천)
- `docs/기획서.md` — 요구사항, 범위(MVP vs 향후), 데이터 소스, 완료 기준
- `docs/아키텍처.md` — 모듈 분해, 데이터 흐름, 예측 파이프라인, API 설계
> 이 CLAUDE.md와 위 문서가 충돌하면 **문서가 우선**. 설계가 바뀌면 문서를 먼저 고치고 이 파일을 갱신.

## 절대 깨면 안 되는 설계 불변식
1. **스코어 매트릭스 = 유일한 진실의 원천.** Elo는 λ(기대득점)만 산출한다. 승/무/패와 스코어라인은 **반드시** `score_matrix.py`의 매트릭스에서 읽는다. Elo나 다른 곳에서 승률을 직접 계산하지 말 것 (승률·스코어 모순 방지).
2. **영역 매핑** (M[x][y]=P(A가 x골, B가 y골)): A승=하삼각 `tril(M,-1)`, 무=`trace(M)`, B승=상삼각 `triu(M,1)`. 헷갈리기 쉬우니 단위 테스트로 고정.
3. **LLM은 확률을 절대 못 건드린다.** `llm/augmenter.py`는 득점자 재랭킹 + 해설만. temperature 0, JSON 스키마 제약, 스쿼드 멤버십 검증 실패 시 통계 랭킹으로 폴백. 확률·스코어는 앱이 verbatim 통과.
4. **국가명 정규화는 1급 모듈** (`core/name_resolver.py`). 모든 소스(elo/football-data/api-football/wikipedia)는 팀명이 다르므로 표준키(ISO alpha-3) ↔ 소스별 식별자 매핑을 `core/aliases.py`에 집중. 가장 조용히 깨지는 지점. 새 팀에 fd_id/api_football_id 추가 시 aliases.py 보강.
5. **graceful degradation.** 키 없어도 동작해야 한다: Anthropic 키 없음→통계+템플릿 해설, API-Football 키 없음→football-data.org+Elo. 각 Provider/Augmenter는 `available()`로 자가 판단.
6. **임의 대진 지원.** 예정 경기에 의존하지 말 것. 두 팀을 각각 독립 조회(H2H는 부가정보).

## 시크릿 & 데이터
- 키는 `.env`에만 (`.gitignore`됨). **절대 커밋 금지.** 예시는 `.env.example`.
- 외부 호출은 **반드시** `data/cache.py`의 TTL 캐시 경유 (무료 한도 100/일, 10/분 보호).
- 캐시 TTL: Elo·스쿼드 24h, 결과 6h, 부상/폼 속보는 캐시 안 함(온디맨드 웹검색).
- `data_snapshots/`의 동봉 Elo 스냅샷은 오프라인 폴백·재현용.

## 코드 컨벤션
- Python 3.11+, 타입 힌트 필수. 도메인 모델은 `core/models.py`의 `@dataclass`.
- 외부 소스는 `data/base.py`의 `DataProvider` 인터페이스를 구현 (격리). 엔진·LLM은 외부 I/O를 몰라야 함.
- 보정 상수(β0≈0.262, β1≈0.40, ρ≈-0.05 등)는 `engine/config.py`에 집중 — 코드에 하드코딩 금지.
- 새 의존성·디렉터리 추가 시 `docs/아키텍처.md`의 구조와 일치시킬 것.

## 명령어 (검증됨 — 구현 진행하며 갱신)
가상환경(Windows): `python -m venv .venv` → `.venv\Scripts\activate`
- 설치(개발): `.venv/Scripts/python.exe -m pip install -e ".[dev]"` (LLM 포함: `.[dev,llm]`)
- 테스트: `.venv/Scripts/python.exe -m pytest -q`  ✅ 동작 (현재 139 passed)
- 보정: `.venv/Scripts/python.exe -m soccermind.calibrate WC` (과거경기 replay→fit, FOOTBALL_DATA_TOKEN 필요)
- 린트: `.venv/Scripts/python.exe -m ruff check .`  ✅ 동작
- 실행(API+UI): `.venv/Scripts/python.exe -m uvicorn soccermind.api.app:app --reload` → http://127.0.0.1:8000  ✅ 동작
- 헬스체크: `GET /healthz` (provider/augmenter 가용 상태), 예측: `GET /api/predict?team_a=대한민국&team_b=브라질`
> 통계 엔진은 순수 Python(math/difflib stdlib만) — numpy 미사용, 의존성 없이 테스트 가능.

## 작업 규칙
- **테스트 필수**: 주요 기능은 빠짐없이 테스트케이스 추가, **커밋 전 `pytest` 전체 통과 확인**. 실패 상태로 커밋 금지.
- 외부 네트워크 의존 코드는 파싱(순수)과 fetch(I/O)를 분리하고, 테스트는 픽스처/주입으로 한도 소모 없이.
- 응답·문서·커밋 메시지는 **한국어** (코드 식별자는 영어).
- 커밋·푸시는 사용자가 요청할 때만. 레포: https://github.com/inchoel/SoccerMind
- 현재 상태: **MVP + 보정/백테스트 + 토너먼트 + 과거경기 Elo replay 보정 완료, 114 tests.** 보정 흐름: results_provider(football-data 결과)→rating_history.replay(경기전 레이팅 재구성)→calibration.fit. CLI: `soccermind.calibrate`. 다음 후보: API-Football 통합, 토너먼트 UI, 피팅 상수 영속화.
