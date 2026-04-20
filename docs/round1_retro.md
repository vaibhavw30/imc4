# Round 1 Retrospective

**Sprint:** Sprint 1 (Round 1 retro + Round 2 data setup)
**Date:** 2026-04-19
**Author:** retro notes, not a postmortem — written with all IMC data we have
**Scope:** Round 1 only. Round 2 context lives in `round2_context.md`.

---

## Executive summary

We submitted **v4** to Round 1: the v1 market-making core for both products,
plus a slow-EMA directional overlay on INTARIAN_PEPPER_ROOT that wakes up only
when drift is materially larger than tick noise. On IMC's live evaluation the
algorithmic side produced **55,178 XIREC** (Osmium 15,664, Pepper 39,514). The
manual challenge submissions are expected to return ~**87,995** (Flax 9,999 +
Ember 77,996), but the official IMC number for manual is not yet visible to us.
Combined working estimate heading into Round 2: ~**143k XIREC**.

The main lesson: a conservative, dormant-on-flat-days overlay with a threshold
calibrated to realistic live noise (not to the pre-deadline test day) did
exactly what it was designed to do when Pepper drifted +1001 ticks on eval day.

---

## Submission history

Pre-deadline test day was low-drift; real eval day was high-drift on Pepper.

| Version | Description | Pre-deadline test PnL | Decision | Reasoning |
|---|---|---:|---|---|
| **v1** | Pepper MM only (take + make + inventory-widening), no directional component. | 5,321 | Shipped then, retained as fallback. | Known-good baseline. Clean MM; no overlay = no regime risk. |
| **v2** | v1 with dead-zone relaxation (wider min_edge or loosened wall detection — the relaxation experiment). | 4,638 | Reverted. | Strictly worse on the test day. Not worth the code churn; no upside story. |
| **v4** | v1 MM core + EMA drift overlay on Pepper. Overlay biases one side's passive quote size by `+PEPPER_DRIFT_BIAS_SIZE` when `|wall_mid − EMA|` exceeds `PEPPER_DRIFT_THRESHOLD`. | 5,321 | **Shipped.** | v1-equivalent on flat days (overlay dormant), optional upside on drift days. No downside vs v1 in the test regime. |

**v4 parameters (shipped):**

- `PEPPER_EMA_ALPHA = 0.005` (~200-tick half-life — slow enough to ignore tick noise, fast enough to track intra-day drift)
- `PEPPER_DRIFT_THRESHOLD = 8.0` (≈0.28σ at live-scale tick std≈29 — below this we treat the EMA gap as noise)
- `PEPPER_DRIFT_BIAS_SIZE = 8` (extra passive size on the drift-favored side; modest vs v1 `base_size=12` so whipsaw is bounded)

v4 also has a `state.timestamp == 0` EMA reset so the merged 3-day backtest
doesn't benefit from cross-day EMA carry-over that wouldn't exist live.

---

## Live evaluation result breakdown

| Source | PnL (XIREC) |
|---|---:|
| Algo total | **55,178** |
| — ASH_COATED_OSMIUM | 15,664 |
| — INTARIAN_PEPPER_ROOT | 39,514 |

Market regime on eval day:

- **Osmium:** near-flat, final-vs-opening drift **−6 ticks**. Expected for a stable product with a fixed anchor near 10,000. Osmium strategy is pure take-+-make around `OSMIUM_FAIR_VALUE = 10_000`, so a flat day = the standard MM harvest.
- **Pepper Root:** strong upward drift, **+1001 ticks** from open to close.

**Why the v4 overlay fired (correctly):**

With live tick std ≈ 29, a +1001 drift is on the order of ~35σ. The overlay
threshold was set at 8, ≈0.28σ — well inside the "real drift" regime. The
EMA lagged the climbing wall_mid, so the signal `wall_mid − EMA` stayed
positive and above threshold for most of the day, biasing passive buy size
upward. That is what the overlay was built to do; the result — a 39,514
Pepper print vs a 15,664 Osmium print — is consistent with the overlay
capturing the drift component that the pure-MM v1 would have left on the
table.

Caveat: per-product numbers above are totals, not decomposed into "MM edge"
vs "inventory × drift" components. We don't have the per-tick position trace
from the live run, so we can't say exactly how much of the 39,514 came from
quote-capture vs. inventory drifting up. Next-round instrumentation should
fix that if we want to tune the overlay further.

---

## Manual challenge submission

| Container | Action | Price | Volume | Expected PnL |
|---|---|---:|---:|---:|
| DRYLAND_FLAX | Buy | 30 | 9,999 | 9,999 |
| EMBER_MUSHROOM | Buy | 17 | 19,999 | 77,996 |

**Combined expected:** ~87,995. **Actual manual result:** TBD — IMC had not
surfaced a split manual number to us at the time of writing. The ~143k
cumulative estimate assumes the expected manual PnL lands; confirm before
relying on it.

---

## What we got right

1. **Modular repo structure.** `algo/strategies/*` with a `Strategy` base
   class kept Osmium and Pepper in separate files, so tuning one did not
   touch the other. The flat `dist/bigballers.py` is generated from this
   source via `scripts/flatten.py`.
2. **Careful EDA before strategy code.** We did not write a single Pepper
   order until we had looked at wall_mid drift, tick noise std, and the
   order-book wall structure in `analysis/explore.py`.
3. **Matcher-comparison diagnostic.** Ran both `--match-trades all` and
   `--match-trades worse` side-by-side to rule out backtester matcher
   artifacts as an explanation for Pepper's day-to-day volatility. Both
   matchers told the same story.
4. **Cold-start diagnostic.** Verified that the EMA reset on `timestamp == 0`
   actually fires correctly and that the first-tick behavior matches v1
   (overlay dormant until EMA has at least one sample).
5. **Conservative threshold (8) rather than tuning to the pre-deadline
   test day (3).** The test day was low-drift; a threshold of 3 would have
   looked better on that day but would have been noise-triggering in
   any realistic live regime. Picked 8 against the 0.28σ rule, accepted
   the test-day PnL parity with v1, and shipped.
6. **Kept v1 as a known-good fallback** through the whole sprint. At every
   fork we could have reverted to v1 in minutes.
7. **Did not panic-tune at 3 AM when v2 underperformed.** Reverted v2
   cleanly, slept, re-evaluated the next morning, chose v4 on fundamentals.

---

## What we got wrong (or would do differently)

1. **Initially recommended manual `Sp=1`** without thinking through the
   opponent bid distribution. The actual submission corrected this, but
   the first-pass reasoning was sloppy.
2. **Over-investigated the "is this overfitting?" question.** The EDA and
   test-day numbers were clean; we spent extra cycles re-confirming
   something the data had already settled.
3. **v2 dead-zone relaxation cost ~1 hour** for a net-negative change.
   Should have asked "what specifically will this fix?" before writing it.
4. **Should have read the Round 2 wiki earlier.** The MAF mechanism uses a
   `bid()` method on Trader — this is materially different from submitting
   via traderData and it will need code changes in Sprint 2. Discovering
   this during retro rather than during Round 1 means Sprint 2 starts
   cold on the topic.
5. **No per-tick position trace saved from the live eval.** We can't fully
   decompose the Pepper 39,514 into MM vs inventory components because
   the live logs we have only give totals. Add this instrumentation for
   Round 2.

---

## Reusable infrastructure for Round 2+

All of the following is in-tree and does not require changes for Round 2:

- **`algo/strategies/base.py` — `Strategy` base class.** Adding a new
  strategy is one file plus one line in `Trader.__init__`.
- **`scripts/flatten.py` — flatten modular → single-file.** Concatenates
  `algo/logger.py`, `algo/utils/*`, `algo/strategies/base.py`, and the
  two concrete strategies into `dist/bigballers.py`. IMC requires single
  file upload; flattener keeps the modular source authoritative.
- **`analysis/explore.py` — EDA pipeline.** wall_mid, tick std, drift
  summaries for any `prices_round_N_day_D.csv`.
- **`analysis/load_data.py`** — uniform CSV loader. Works on both Round 1
  and Round 2 data; header format verified identical.
- **`analysis/parse_log.py` — backtest log parser.** Pulls per-product PnL,
  position trace, and trade list out of `prosperity4btest` output.
- **Diagnostic playbook:**
  - cold-start / EMA-reset verification,
  - per-day flip counts + position stats,
  - matcher-comparison (`all` vs `worse`) to rule out simulator artifacts,
  - per-product per-day PnL table vs pre-submission expectation.
- **`run_backtest.sh`** — timestamped invocation with `PYTHONPATH=.` so
  imports resolve when prosperity4btest executes `algo/trader.py`.

---

## Repo state at retro close (Sprint 1)

Verified by direct inspection, not assumption:

- `algo/trader.py` — v4 Trader, two strategies registered, no `bid()` method.
- `algo/strategies/pepper_root.py` — v4 overlay present, thresholds
  `ALPHA=0.005 / THRESHOLD=8.0 / BIAS_SIZE=8`.
- `dist/bigballers.py` — 517 lines, flat v4 submission.
- **No `MARKET_ACCESS_FEE` constant anywhere, no `def bid` method.** The
  Sprint 1 brief predicted that v4 had "broken MAF" writing into
  `traderData`; grep says otherwise. The current repo is clean of MAF
  code altogether. Sprint 2 will add the correct `bid()` method to the
  Trader class from scratch.
- **Round 1 v4 practice backtest reproduces exactly:** 142,102 XIREC
  (worse matcher, merged PnL, days −2/−1/0). Day split: 34,792 / 80,193
  / 27,117. No repo drift since the submission snapshot.

---

## Open questions (not answered by this retro)

1. What is the **actual** manual-challenge PnL from IMC? Our 87,995 is
   a pre-submission expected value, not a post-hoc confirmation.
2. What is our **current cumulative standing** and **leaderboard position**
   after Round 1? The ~143k working number assumes expected manual; the
   200k qualification gate assumes that number is correct.
3. Does the Round 2 market regime look more like Round 1 practice days
   or Round 1 live day? (Sprint 3 will answer this with EDA on
   `data/ROUND_2/`. Not in-scope for Sprint 1.)
4. Is the leaderboard **cumulative** across rounds, or does it **reset**
   per round? Matters for how much algorithmic PnL we need to prioritize
   in Round 2. Check the ARIA uplink / Round 2 wiki.
5. What do other teams' MAF bids look like? Not observable pre-round;
   we will need a prior and a fallback plan for Sprint 2.
