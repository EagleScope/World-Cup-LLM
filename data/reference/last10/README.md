# Last-10 form/goals — knockout teams (source data)

Source for the registered pack fields **`recent form (last 10, W-D-L)`** and
**`goals for/against (last 10)`** (§11). Committed **after** the pre-registration
tag; the frozen tag `c5cde21` and the OSF registration are untouched.

## Files
- `World_Cup_2026_Last10_Knockout_R32_VERIFIED.xlsx` — author-compiled and
  independently re-verified source (provided 2026-06-28). 32 teams × 10 games:
  a `Summary` sheet and a per-game `All Matches` sheet (date, competition, venue,
  opponent, score, GF, GA, result, notes).
- `last10_R32.json` — the **canonical, convention-applied** derivation the freeze
  pipeline reads. Per team: W-D-L, GF/GA, form string, and every game with an
  `adjusted_shootout` flag.

## Verification (passed)
- 32 teams, exactly 10 games each (320). Every team's Summary W-D-L / GF / GA /
  form is reproduced exactly by its raw games (0 mismatches).
- Leakage-free for the Round of 32: most-recent game 2026-06-27; **zero** games
  dated ≥ 2026-06-28 (no knockout results leaked in); games ordered newest→oldest.
- Senior A-team, official, competitive + friendlies only (World Cup, AFCON, WC
  qualifiers/playoffs, inter-confederation playoff, friendlies). No youth/club.
- Matches the frozen match-73 pack exactly: South Africa 2-4-4 9/12, Canada 4-5-1 16/6.

## Locked convention — penalty shootouts (2026-06-28)
**`penalties_as_draw`:** a match level after 90 minutes counts as a **DRAW** for
W-D-L; the shootout decides progression only. **Goals are regulation-time** (a
shootout adds none). Applied in `last10_R32.json`; affects only the two teams with
shootouts in their last 10:

| Team | as submitted | after rule | GF/GA |
|---|---|---|---|
| Morocco | 6-3-1 | **5-4-1** | 16/7 (unchanged) |
| Bosnia & Herzegovina | 5-4-1 | **3-6-1** | 16/12 (unchanged) |

All 30 other teams (and match 73) are unchanged.

## Scope & rolling window
This snapshot is the **Round of 32** last-10. Form rolls forward: a team's R16
last-10 will include its R32 game, so **later rounds need a refreshed table**. At
each match's freeze we take the 10 most recent games dated **before that fixture's
pre-kickoff capture** for the two teams, and record this file as the source in the
match's `sources.json`.
