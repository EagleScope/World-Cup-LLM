"""
analysis.py — secondary analyses (§14 "Secondary"), all pure and testable.

Builds on the frozen primitives (scoring_frozen) without modifying them:

  reasoning_effect      — within-model low-vs-high difference in RPS and
                          calibration error (Gemini excluded; §6/§14, H2)
  conditioning_effect   — withheld-vs-supplied-arm difference in RPS and Brier,
                          and change in divergence from the market (§7/§14, H4)
  anchoring_correlation — correlation of model probabilities with the Elo
                          baseline and with the market (§14, H5)
  forecast_encompassing — does market+model beat market alone? logistic
                          encompassing test on the binary advance outcome (H5)

Primary calibration/accuracy/skill/equivalence live in scoring_frozen.py (frozen).
This module is the registered SECONDARY layer and may evolve up to lock.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence

import numpy as np
from scipy import optimize, stats

from config import config as C
from src.scoring_frozen import diebold_mariano, rps_three_way, brier_multiclass, ece_mce


# --------------------------- reasoning effect (H2) ------------------------ #
def reasoning_effect(rps_low: Sequence[float], rps_high: Sequence[float],
                     p_adv_low: Sequence[float], p_adv_high: Sequence[float],
                     advanced: Sequence[int]) -> Dict:
    """Within-model low-vs-high contrast (§14). Positive mean_rps_diff => high
    effort has WORSE (higher) RPS than low. DM(HLN) tests the RPS difference;
    ECE delta reports the calibration change."""
    rl = np.asarray(rps_low, float)
    rh = np.asarray(rps_high, float)
    dm = diebold_mariano(rh, rl)              # high vs low: +stat => high worse
    ece_low = ece_mce(p_adv_low, advanced)["ece"]
    ece_high = ece_mce(p_adv_high, advanced)["ece"]
    return {
        "mean_rps_low": float(rl.mean()), "mean_rps_high": float(rh.mean()),
        "mean_rps_diff_high_minus_low": float(rh.mean() - rl.mean()),
        "dm_high_vs_low": dm,
        "ece_low": ece_low, "ece_high": ece_high,
        "ece_delta_high_minus_low": ece_high - ece_low,
    }


# ------------------------- conditioning effect (H4) ----------------------- #
def conditioning_effect(rps_primary: Sequence[float], rps_cond: Sequence[float],
                        brier_primary: Sequence[float], brier_cond: Sequence[float],
                        model_p_primary: Sequence[Sequence[float]],
                        model_p_cond: Sequence[Sequence[float]],
                        market_p: Sequence[Sequence[float]]) -> Dict:
    """Withheld (primary) vs supplied (conditioning) arm (§7/§14, H4). H4 predicts
    supplying the market LOWERS Brier/RPS and pulls forecasts toward the market."""
    rp = np.asarray(rps_primary, float); rc = np.asarray(rps_cond, float)
    bp = np.asarray(brier_primary, float); bc = np.asarray(brier_cond, float)

    def mean_div(model_p):
        mp = np.asarray(model_p, float); mk = np.asarray(market_p, float)
        return float(np.mean(np.sum(np.abs(mp - mk), axis=1)))  # L1 divergence

    return {
        "mean_rps_diff_cond_minus_primary": float(rc.mean() - rp.mean()),
        "mean_brier_diff_cond_minus_primary": float(bc.mean() - bp.mean()),
        "dm_rps_cond_vs_primary": diebold_mariano(rc, rp),
        "divergence_primary": mean_div(model_p_primary),
        "divergence_cond": mean_div(model_p_cond),
        "divergence_drop": mean_div(model_p_primary) - mean_div(model_p_cond),
    }


# ------------------------- anchoring correlation (H5) --------------------- #
def anchoring_correlation(model_three_way: Sequence[Sequence[float]],
                          elo_three_way: Sequence[Sequence[float]],
                          market_three_way: Sequence[Sequence[float]]) -> Dict:
    """Correlation of the model's P(A win) with the Elo baseline and the market
    (§14, H5). High correlation when the market is withheld indicates anchoring."""
    m = np.asarray(model_three_way, float)[:, 0]
    e = np.asarray(elo_three_way, float)[:, 0]
    k = np.asarray(market_three_way, float)[:, 0]
    return {
        "corr_model_vs_elo": float(np.corrcoef(m, e)[0, 1]),
        "corr_model_vs_market": float(np.corrcoef(m, k)[0, 1]),
    }


# ---------------------- forecast-encompassing test (H5) ------------------- #
def _logit(p: np.ndarray) -> np.ndarray:
    lo, hi = C.PRED_BOUNDS
    p = np.clip(p, lo, hi)
    return np.log(p / (1 - p))


def _logit_mle(X: np.ndarray, y: np.ndarray):
    """Stable logistic MLE; returns (beta, loglik)."""
    def nll(b):
        eta = X @ b
        return float(np.sum(np.logaddexp(0.0, eta) - y * eta))

    def grad(b):
        eta = np.clip(X @ b, -30, 30)
        mu = 1 / (1 + np.exp(-eta))
        return X.T @ (mu - y)

    with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
        res = optimize.minimize(nll, np.zeros(X.shape[1]), jac=grad, method="L-BFGS-B")
    return res.x, -res.fun


def forecast_encompassing(market_p_adv: Sequence[float], model_p_adv: Sequence[float],
                          advanced: Sequence[int]) -> Dict:
    """Does the model add information beyond the market? (§14, H5)

    Logistic regression of the binary advance outcome on logit(market) and
    logit(model). Likelihood-ratio test (chi2, 1 df) of adding the model to a
    market-only model. A non-significant model term (and ~0 coefficient) means
    the market encompasses the model (the parroting result)."""
    y = np.asarray(advanced, float)
    lm = _logit(np.asarray(market_p_adv, float))
    lo = _logit(np.asarray(model_p_adv, float))
    n = len(y)
    X_market = np.column_stack([np.ones(n), lm])
    X_full = np.column_stack([np.ones(n), lm, lo])
    _, ll_market = _logit_mle(X_market, y)
    beta_full, ll_full = _logit_mle(X_full, y)
    lr = 2.0 * (ll_full - ll_market)
    p_value = float(stats.chi2.sf(max(lr, 0.0), df=1))
    return {
        "model_coefficient": float(beta_full[2]),     # weight on the model term
        "market_coefficient": float(beta_full[1]),
        "lr_stat": float(lr), "p_value": p_value,
        "model_adds_info": p_value < C.ALPHA,
    }
