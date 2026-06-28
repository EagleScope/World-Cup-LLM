# Design Note 001 (repo) — Polymarket per-match 3-way as an EXPLORATORY benchmark

> **This is a repo-level methods note. It is NOT filed, registered, or amended on
> OSF.** The immutable OSF pre-registration is unchanged (see *Status of the OSF
> registration* below). The file keeps the name `AMENDMENT_001_polymarket_3way.md`
> for sequence/history only — it documents a repo-level addition to the analysis
> code and data, not an amendment to the OSF registration.

- **Date:** 2026-06-28
- **Scope:** repo only. Documents an **exploratory** addition under
  `METHODS_PROTOCOL_v1.md` §13 (Baselines). Does not change the registered method.
- **Status of the OSF registration:** **UNCHANGED and untouched.** The original
  pre-registration — protocol + frozen scoring + pipeline code + frozen R32 pack,
  captured at git tag `pre-registration-v1.0` (commit `c5cde21`) and registered on
  OSF — remains the **sole immutable pre-registration**. Nothing is filed, updated,
  amended, or attached on OSF. The frozen tag is never rewritten.
- **Consequence — exploratory status:** because the Polymarket per-match 3-way is
  **not** part of that immutable OSF registration, it is reported strictly as an
  **EXPLORATORY (secondary) benchmark** — clearly labeled as such, and never
  presented as a pre-registered or confirmatory comparison.
- **Timing relative to data:** recorded **before any knockout match resolved.**
  Match 73 (South Africa vs Canada) kicks off 2026-06-28 19:00 UTC; this note rests
  only on the pre-kickoff market **structure** captured at 16:51 UTC — no result
  exists yet.

## The registered (OSF-locked) market baselines — unchanged

These remain exactly as pre-registered in §13 and are the **confirmatory** market
benchmarks:

- **Polymarket** → benchmarks **advancement** and **outright winner**.
- **Pinnacle closing line** → benchmarks the **90-minute three-way (1X2)** result.

This note changes none of them. Pinnacle remains the registered three-way benchmark.

## The exploratory addition

We additionally capture and report the **Polymarket per-match three-way (1X2)** —
`A_WIN / DRAW / B_WIN` — as an **exploratory** benchmark, reported **alongside**
(never replacing) the registered baselines, and **separately, never pooled** with
them. In any results table it is flagged exploratory and kept distinct from the
confirmatory (OSF-registered) comparisons.

**Why exploratory rather than registered.** §13 carried an explicit *"verify during
build"* item — *"Polymarket's actual 2026 knockout market structure (likely
advancement, not a three-way with a draw). If Polymarket does not price the
three-way, Pinnacle is the sole three-way benchmark…"* The live structure turned
out to include a liquid Polymarket three-way. Rather than retrofit that discovery
into the immutable OSF registration (which we are deliberately leaving untouched),
we report the Polymarket three-way as exploratory.

**What is unchanged regardless:** de-vig method (proportional LOCKED primary;
odds-ratio + Shin sensitivity), capture timing (matched pre-kickoff timestamp with
the short pre-resolution exclusion), and the scoring battery (§14 — skill scores
RPSS/BSS computed vs each market separately). No model-side method, prompt, pack,
aggregation, or calibration metric is affected by this note.

## Rationale (recorded)

The §13 working assumption that "Polymarket prices advancement, not a 3-way with a
draw" proved **factually wrong**. At the match-73 matched pre-kickoff capture,
Polymarket posts a **liquid per-match three-way** — three binary Yes/No legs
(team-A win / draw / team-B win) — with ~**$12.9M** volume on the favourite leg and
a booksum of 0.995 (≈0.5% under-round), while the Polymarket **advancement** market
(*Nation to Reach Round of 16*) is **thin** (~**$28k**). Ignoring a deeper, more
liquid Polymarket three-way that grades exactly the outcome the models forecast
would discard real information.

This is a **market-structure fact**, observed **before any knockout match
resolved**, so it is **independent of any result** and is not a result-dependent
(post-hoc / HARKing) choice. That is what makes it a principled *exploratory*
addition — but it stays exploratory, not confirmatory, precisely because it is not
part of the locked OSF registration.

## What gets captured (per match, from this match onward)

At the matched pre-kickoff timestamp:
1. **Polymarket per-match 3-way** → de-vigged `A_WIN / DRAW / B_WIN` (NEW — exploratory).
2. **Polymarket advancement** → de-vigged `ADV_A / ADV_B` (registered, confirmatory).
3. **Polymarket outright / champion** (registered, confirmatory).
4. **Pinnacle closing line** 3-way (registered, confirmatory).

Each line stores the raw JSON + SHA-256 + capture timestamp + per-market prices,
de-vigged under the locked proportional method plus the odds-ratio and Shin
sensitivity methods.

## Match 73 (South Africa = A, Canada = B), parsed offline from the 16:51Z archive

Leakage-free (parsed from the pre-kickoff raw search; no value re-fetched), primary
(proportional) de-vig:

| Benchmark | A_WIN | DRAW | B_WIN | ADV_A | ADV_B | Status |
|---|---|---|---|---|---|---|
| Polymarket per-match 3-way | 0.166 | 0.276 | 0.558 | — | — | exploratory |
| Polymarket advancement (reach R16) | — | — | — | 0.247 | 0.753 | registered |

Recorded in `data/markets/R32_73_ZAF_CAN.market.manifest.json`.

## Implementation

Parsers in `src/markets/polymarket.py` (`parse_match_3way`,
`parse_advancement_pair`, `build_match_benchmark`), wired into
`src/markets/capture.py`; offline tests in `tests/test_polymarket_match.py`.
Committed to the repo **after** the pre-registration tag (per the §17 two-tier
timestamp policy); the tag and the OSF registration are never modified.
