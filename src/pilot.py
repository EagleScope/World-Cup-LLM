"""
pilot.py — Stage-1 pilot harness and hard pass gate (§19).

Runs the FULL pipeline on finished group-stage matches and checks:
  - > 95% of responses return exactly the clean five keys (§19, §20.6), and
  - aggregate Brier is stable to within 0.005 between N=10 and N=20.

Proceed to lock / live collection ONLY if both pass. Also reports the measured
per-match token usage (and USD cost once provider prices are confirmed) — the
§18 "true per-match figure" you review before anything larger runs.

Clients are injected, so the gate logic is testable offline; the real pilot run
makes live calls and is gated on PI approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np

from config import config as C
from src import aggregate as AGG
from src import parsing as P
from src import run_aggregate as RA
from src.clients.base import ModelClient
from src.scoring_frozen import brier_multiclass


@dataclass
class PilotMatch:
    match_id: str
    pack_fields: Dict
    result_three_way: List[int]        # one-hot [A win, draw, B win]
    advanced: int                      # did team A advance (1/0)
    market: Optional[Dict] = None


@dataclass
class PilotResult:
    n_calls: int
    n_clean: int
    parse_rate: float
    brier_n10: float
    brier_n20: float
    brier_stability: float
    parse_gate_pass: bool
    brier_gate_pass: bool
    passed: bool
    tokens_per_match: float
    usd_per_match: Optional[float]

    def summary(self) -> str:
        lines = [
            "=" * 64, "PILOT GATE (§19)", "=" * 64,
            f"calls               : {self.n_calls}",
            f"clean five-key rate : {self.parse_rate:.4f}   "
            f"(gate > {C.PILOT_MIN_PARSE_RATE}) -> {'PASS' if self.parse_gate_pass else 'FAIL'}",
            f"Brier N=10 / N=20   : {self.brier_n10:.4f} / {self.brier_n20:.4f}",
            f"Brier stability     : {self.brier_stability:.4f}   "
            f"(gate <= {C.PILOT_BRIER_STABILITY}) -> {'PASS' if self.brier_gate_pass else 'FAIL'}",
            f"tokens / match      : {self.tokens_per_match:.0f}",
            f"USD / match         : {('$%.4f' % self.usd_per_match) if self.usd_per_match is not None else 'PENDING (provider prices)'}",
            "-" * 64,
            f"OVERALL             : {'PASS — proceed' if self.passed else 'FAIL — do not lock/collect'}",
            "=" * 64,
        ]
        return "\n".join(lines)


def run_pilot(clients: Dict[str, ModelClient], matches: List[PilotMatch],
              n: int = C.N_SAMPLES, records_path: Optional[str] = None) -> PilotResult:
    n_calls = 0
    n_clean = 0
    total_tokens = 0
    total_cost = 0.0
    cost_known = True
    brier10: List[float] = []
    brier20: List[float] = []

    for m in matches:
        cells = RA.run_match(clients, m.match_id, m.pack_fields,
                             market=m.market, n=n, records_path=records_path)
        result = np.array([m.result_three_way], dtype=float)   # shape (1,3)
        for cell in cells.values():
            for r in cell.records:
                n_calls += 1
                n_clean += int(r.parse_clean)
                total_tokens += r.usage.total_tokens
                if r.usage.usd_cost is None:
                    cost_known = False
                else:
                    total_cost += r.usage.usd_cost
            samples = RA._renormalized_samples(cell.records)
            if len(samples) >= 20:
                for nn, sink in ((10, brier10), (20, brier20)):
                    agg = AGG.aggregate(samples[:nn], method="median")
                    vec = np.array([[agg[k] for k in C.THREE_WAY_KEYS]], dtype=float)
                    sink.append(float(brier_multiclass(vec, result)[0]))

    parse_rate = n_clean / n_calls if n_calls else 0.0
    b10 = float(np.mean(brier10)) if brier10 else float("nan")
    b20 = float(np.mean(brier20)) if brier20 else float("nan")
    stability = abs(b10 - b20) if brier10 and brier20 else float("inf")

    parse_pass = parse_rate > C.PILOT_MIN_PARSE_RATE
    brier_pass = stability <= C.PILOT_BRIER_STABILITY
    n_matches = max(len(matches), 1)
    return PilotResult(
        n_calls=n_calls, n_clean=n_clean, parse_rate=parse_rate,
        brier_n10=b10, brier_n20=b20, brier_stability=stability,
        parse_gate_pass=parse_pass, brier_gate_pass=brier_pass,
        passed=parse_pass and brier_pass,
        tokens_per_match=total_tokens / n_matches,
        usd_per_match=(total_cost / n_matches) if cost_known else None,
    )
