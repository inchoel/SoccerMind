# SoccerMind ⚽🧠

두 국가명을 입력받아 **승리 국가 · 예상 스코어 · 예상 득점자**를 예측하는, 실시간 데이터 기반 오픈소스 분석 도구.

> 재미용 룰렛이 아니라 **실제 공개 데이터 + 검증된 통계 모델 + LLM 보강**으로 재현 가능하고 설명 가능한 예측을 제공합니다.

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
- **LLM 레이어**는 득점자 재랭킹과 자연어 해설만 담당하며 확률은 변경하지 못함 (temperature 0, 스키마 제약, 스쿼드 검증).

## 데이터 소스

| 소스 | 용도 | 키 |
|------|------|----|
| eloratings.net | 팀 강도(Elo) | 불필요 |
| football-data.org | WC 경기·스쿼드·득점자 (백본) | 무료 자가발급 |
| API-Football | WC 심층 (선택) | 무료 자가발급 |
| Wikipedia API / 웹검색 | 스쿼드·부상·폼 보강 | 불필요 |

football-data.org 키 1개만으로 동작하며, 키가 없어도 통계 예측 + 템플릿 해설로 우아하게 동작합니다.

## 빠른 시작

```bash
python -m venv .venv && .venv\Scripts\activate        # Windows (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"                                # LLM 포함: ".[dev,llm]"
cp .env.example .env                                   # 본인 키 입력 (없어도 통계 예측은 동작)
uvicorn soccermind.api.app:app --reload                # → http://127.0.0.1:8000
pytest -q                                              # 테스트 (현재 73 passed)
```

브라우저에서 **경기 예측**(두 국가 → 승리국·스코어·득점자·해설)과 **토너먼트 우승**(참가국 → 우승확률 랭킹) 두 탭을 사용할 수 있습니다.

```
GET /api/predict?team_a=대한민국&team_b=브라질
GET /api/tournament?teams=브라질,아르헨티나,프랑스,스페인   # 2의 거듭제곱
```

## 문서

- [기획서 (PRD)](./docs/기획서.md)
- [아키텍처 설계](./docs/아키텍처.md)

## 상태

✅ **MVP 구현 완료** — 통계 엔진(Elo→스코어매트릭스) + 국가명 정규화 + 데이터 레이어(Elo/football-data + 캐시) + 오케스트레이터 + LLM augmenter(가드레일) + FastAPI/웹 UI. Python 3.11+.

향후: 모델 보정(과거 경기 피팅)·백테스트, API-Football 통합, 토너먼트 시뮬레이션.

## 라이선스

MIT (예정)
