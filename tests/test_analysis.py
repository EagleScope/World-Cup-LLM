"""Tests for the secondary analyses (§14): reasoning, conditioning, anchoring, H5."""
import numpy as np
import pytest

from src import analysis as AN


def test_reasoning_effect_detects_worse_high():
    rng = np.random.default_rng(0)
    rps_low = rng.uniform(0.1, 0.2, 30)
    rps_high = rps_low + 0.05               # high effort worse (H2 direction)
    adv = rng.integers(0, 2, 30)
    p_low = rng.uniform(0.3, 0.7, 30)
    p_high = rng.uniform(0.3, 0.7, 30)
    r = AN.reasoning_effect(rps_low, rps_high, p_low, p_high, adv)
    assert r["mean_rps_diff_high_minus_low"] == pytest.approx(0.05, abs=1e-9)
    assert r["dm_high_vs_low"]["hln_stat"] > 0       # high worse


def test_conditioning_pulls_toward_market():
    n = 25
    market = np.tile([0.5, 0.3, 0.2], (n, 1))
    # primary far from market, conditioning close to market
    prim = np.tile([0.8, 0.1, 0.1], (n, 1))
    cond = np.tile([0.55, 0.28, 0.17], (n, 1))
    rps_p = np.full(n, 0.20); rps_c = np.full(n, 0.16)
    br_p = np.full(n, 0.40); br_c = np.full(n, 0.32)
    r = AN.conditioning_effect(rps_p, rps_c, br_p, br_c, prim, cond, market)
    assert r["mean_rps_diff_cond_minus_primary"] < 0      # supplying market lowers RPS
    assert r["divergence_drop"] > 0                        # forecasts move toward market


def test_anchoring_correlation_high_when_model_tracks_elo():
    rng = np.random.default_rng(1)
    pa = rng.uniform(0.2, 0.8, 40)
    elo = np.column_stack([pa, 1 - pa - 0.2 * np.ones_like(pa), 0.2 * np.ones_like(pa)])
    model = np.column_stack([pa + rng.normal(0, 0.01, 40), np.full(40, 0.3), np.full(40, 0.2)])
    market = np.column_stack([1 - pa, np.full(40, 0.3), pa])     # anti-correlated
    r = AN.anchoring_correlation(model, elo, market)
    assert r["corr_model_vs_elo"] > 0.95
    assert r["corr_model_vs_market"] < 0


def test_encompassing_market_only_when_model_is_noise():
    rng = np.random.default_rng(2)
    n = 400
    market = rng.uniform(0.2, 0.8, n)
    y = (rng.random(n) < market).astype(int)            # outcome tracks market
    model = rng.uniform(0.2, 0.8, n)                    # model is pure noise
    r = AN.forecast_encompassing(market, model, y)
    assert r["model_adds_info"] is False                # market encompasses noise model
    assert abs(r["model_coefficient"]) < 1.0


def test_encompassing_detects_real_added_info():
    rng = np.random.default_rng(3)
    n = 600
    signal = rng.uniform(0.1, 0.9, n)
    y = (rng.random(n) < signal).astype(int)
    market = np.full(n, 0.5)                            # market uninformative
    model = signal                                      # model carries the signal
    r = AN.forecast_encompassing(market, model, y)
    assert r["model_adds_info"] is True
    assert r["model_coefficient"] > 0
