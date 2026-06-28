# Study results — organisation & regeneration

This folder holds the consolidated **results workbooks** for the WC-2026 LLM
calibration study. The workbooks are a *derived view* — every value is generated
from the canonical JSON files (below), which remain the source of truth.

## How to regenerate

```bash
PYTHONPATH=. python3 scripts/build_results_workbook.py
```

Run it after each round. It scans `data/packs/*.pack.json` and picks up any new
matches automatically — no manual editing.

## Folder layout

```
data/results/
  README.md                                  # this file (committed)
  _local/                                     # gitignored — see "Why gitignored"
    WC2026_LLM_study_ALL.xlsx                 # ONE big aggregate: every match, all sheets
    <Stage>/<match_id>/<match_id>.xlsx        # one workbook per game, nested by stage
```

Concretely:

```
_local/
  WC2026_LLM_study_ALL.xlsx
  Round_of_32/
    R32_73_ZAF_CAN/
      R32_73_ZAF_CAN.xlsx
  Round_of_16/   …            (created as those rounds are played)
  Quarterfinals/ …
  Semifinals/    …
  Final/         …
```

Stage is derived from the match-id prefix: `R32_`→Round_of_32, `R16_`→Round_of_16,
`QF_`→Quarterfinals, `SF_`→Semifinals, `F_`/`FIN_`→Final, `GS_`→Group_Stage.

## What each workbook contains (same sheets in both per-game and aggregate)

| Sheet | Contents |
|---|---|
| `README` | Scope, regeneration command, legend, OSF/scoring status |
| `Matches` | Identity, stage, kickoff/capture timestamps, pack hash, arms run, result (blank until played) |
| `Pack_Inputs` | The byte-identical model inputs (Elo, FIFA, squad value, form, goals, host, rest) + sha256 |
| `Sources` | Per-field provenance (value A/B, source, note) |
| `Markets` | De-vigged benchmarks — **registered (confirmatory)** vs **EXPLORATORY** (peach rows); withheld from models |
| `Forecasts` | Per (model × effort × arm): median + trimmed mean + SD + IQR (five keys), parse rate |
| `Forecasts_Raw` | One row per individual model sample — full provenance (parsed keys, parse_clean, tokens, timestamp) |
| `Cost_Tokens` | Per provider: calls + input/output/reasoning tokens + USD (estimate), with `SUM` totals |
| `Scoring` | **STUB** — post-resolution only; RPS/Brier/log + skill vs each market (filled by the §14 battery) |

Legend: `A`/`B` = TEAM A / TEAM B; `A_WIN/DRAW/B_WIN` = 90-minute 1X2; `ADV_*` =
advances; peach = exploratory; `USD*` = estimate (token counts are exact).

## Canonical source files (source of truth)

| Data | Location | In frozen tag? |
|---|---|---|
| Frozen model-input pack + sha256 + timestamp | `data/packs/<match_id>.pack.{txt,json}` | **Yes** — `c5cde21` (immutable) |
| Per-field sources | `data/packs/<match_id>.sources.json` | **Yes** |
| Raw Elo snapshot (archived bytes + hash) | `data/packs/<match_id>.elo/` | **Yes** |
| Market benchmark (raw + de-vigged, Pinnacle + Polymarket) | `data/markets/<match_id>.market.manifest.json` | No — post-tag commit |
| Forecast aggregates (median/trimmed/SD/IQR + cost) | `data/forecasts/_local/<match_id>.primary.aggregates.json` | No — gitignored, local |
| Raw per-sample forecasts | `data/forecasts/_local/<match_id>.primary.jsonl` | No — gitignored, local |

## Why `_local/` is gitignored

The workbooks bundle the forecast results, which are **unscored** and held locally
(forecasts are committed/scored only per the study's release policy). The workbooks
are fully reproducible from the canonical files at any time, so they don't need to
be version-controlled. This `README.md` **is** committed so the organisation itself
lives in the repo.

## Scoring

Nothing in any workbook is scored against a result. The `Scoring` sheet is a
pre-keyed stub; after each match resolves it is populated by the **frozen §14
battery** (RPS primary, Brier, log score, calibration, and skill scores RPSS/BSS
computed vs **each market separately**, never pooled).
