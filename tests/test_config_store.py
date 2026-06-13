"""보정 상수 영속화 검증 — save/load_config + build_service 반영."""

from dataclasses import replace

from soccermind.engine.config import (
    DEFAULT_CONFIG,
    load_config,
    save_config,
)


def test_save_load_round_trip(tmp_path):
    path = tmp_path / "cfg.json"
    cfg = replace(DEFAULT_CONFIG, beta1=0.55, rho=-0.08)
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded.beta1 == 0.55
    assert loaded.rho == -0.08
    # 나머지 필드는 기본값 유지
    assert loaded.baseline_total_goals == DEFAULT_CONFIG.baseline_total_goals


def test_load_missing_returns_default(tmp_path):
    loaded = load_config(tmp_path / "absent.json")
    assert loaded == DEFAULT_CONFIG


def test_load_partial_overlay(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text('{"beta1": 0.7}', encoding="utf-8")
    loaded = load_config(path)
    assert loaded.beta1 == 0.7
    assert loaded.rho == DEFAULT_CONFIG.rho  # 명시 안 한 필드는 유지


def test_load_ignores_unknown_keys(tmp_path):
    path = tmp_path / "extra.json"
    path.write_text('{"beta1": 0.6, "nonsense": 123}', encoding="utf-8")
    loaded = load_config(path)
    assert loaded.beta1 == 0.6


def test_load_corrupt_returns_base(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert load_config(path) == DEFAULT_CONFIG


def test_build_service_uses_loaded_config(tmp_path):
    from soccermind.config.settings import build_service

    path = tmp_path / "cfg.json"
    save_config(replace(DEFAULT_CONFIG, beta1=0.7), path)
    svc = build_service(config_path=str(path))
    assert svc.cfg.beta1 == 0.7


def test_calibrate_result_persists(tmp_path):
    import itertools

    from soccermind.calibrate import calibrate_from_results
    from soccermind.engine.rating_history import MatchResult

    results = [
        MatchResult(["A", "B", "C", "D"][hi], ["A", "B", "C", "D"][lo], 2, 0)
        for _ in range(12)
        for hi, lo in itertools.combinations(range(4), 2)
    ]
    res = calibrate_from_results(results)
    path = tmp_path / "fitted.json"
    save_config(res.fitted, path)
    assert load_config(path).beta1 == res.fitted.beta1
