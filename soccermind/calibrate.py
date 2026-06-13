"""모델 보정 러너 + CLI.

과거 경기 결과 → Elo replay(경기 전 레이팅 재구성) → β1·ρ 그리드서치 fit.
CLI: `python -m soccermind.calibrate WC` (FOOTBALL_DATA_TOKEN 필요).
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine.calibration import BacktestReport, backtest, fit
from .engine.config import CONFIG_PATH, DEFAULT_CONFIG, ModelConfig, save_config
from .engine.rating_history import MatchResult, replay

MIN_MATCHES = 30  # 보정에 필요한 최소 경기 수


@dataclass(frozen=True)
class CalibrationResult:
    fitted: ModelConfig
    report_before: BacktestReport
    report_after: BacktestReport
    n_matches: int


def calibrate_from_results(
    results: list[MatchResult],
    cfg: ModelConfig = DEFAULT_CONFIG,
    base_rating: float = 1500.0,
) -> CalibrationResult:
    """결과 → replay → fit. 보정 전/후 백테스트 리포트 포함."""
    _, matches = replay(results, base_rating=base_rating, cfg=cfg)
    if len(matches) < MIN_MATCHES:
        raise ValueError(f"보정에 최소 {MIN_MATCHES}경기 필요 (받음: {len(matches)})")
    fitted, _ = fit(matches, cfg)
    return CalibrationResult(
        fitted=fitted,
        report_before=backtest(matches, cfg),
        report_after=backtest(matches, fitted),
        n_matches=len(matches),
    )


def _main(argv: list[str]) -> int:
    from .config.settings import load_dotenv_if_present
    from .data.results_provider import ResultsProvider

    load_dotenv_if_present()
    code = argv[1] if len(argv) > 1 else "WC"
    provider = ResultsProvider()
    if not provider.available():
        print("FOOTBALL_DATA_TOKEN 이 필요합니다 (.env 에 설정).")
        return 1

    results = provider.fetch_competition(code)
    print(f"[{code}] 종료 경기 {len(results)}건 수집")
    try:
        res = calibrate_from_results(results)
    except ValueError as e:
        print(f"보정 실패: {e}")
        return 1

    print(f"경기 수: {res.n_matches}")
    print(f"보정 전  RPS={res.report_before.rps:.4f}  정확도={res.report_before.accuracy:.3f}")
    print(f"보정 후  RPS={res.report_after.rps:.4f}  정확도={res.report_after.accuracy:.3f}")
    print(f"피팅 상수: beta1={res.fitted.beta1}  rho={res.fitted.rho}")

    save_config(res.fitted, CONFIG_PATH)
    print(f"저장됨 → {CONFIG_PATH} (다음 기동부터 예측에 반영)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    raise SystemExit(_main(sys.argv))
