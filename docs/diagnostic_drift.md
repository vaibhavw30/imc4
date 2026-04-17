# Drift diagnostic — is the 101k Pepper PnL real or cross-day anchor leakage?

**Date:** 2026-04-16
**Question:** The combined 3-day backtest produced 101,414 PnL (Osmium 42,602 + Pepper 58,812) — 10× the Discord consensus for basic MM. Is the Pepper PnL genuine intra-day edge, or is the +1000/day anchor drift (10500 → 11500 → 12500) leaking in via cross-day position carry?

## TL;DR

**Drift delta = 0 on both products. Ship as-is.** Each single-day backtest, run in isolation with position starting at 0, produces PnL that matches the combined-run per-day numbers *exactly*. There is no cross-day holding effect. The 101k is what our MM strategy actually earns on this practice data, day by day.

The Pepper day −1 outlier (47k) is real single-day PnL, not an artifact of anchor drift carry-over. Whether that PnL generalizes to live is a separate question for Sprint 2 (visualizer sanity-check) — this diagnostic only rules out drift leakage.

---

## Comparison table

| Product | Day −2 | Day −1 | Day 0 | Single-day sum | Combined run | Drift delta |
|---|---:|---:|---:|---:|---:|---:|
| ASH_COATED_OSMIUM | 13,183 | 15,569 | 13,850 | **42,602** | 42,602 | **0** |
| INTARIAN_PEPPER_ROOT | 4,298 | 47,228 | 7,286 | **58,812** | 58,812 | **0** |
| Total | 17,482 | 62,797 | 21,136 | **101,414** | 101,414 | **0** |

Drift delta = `Combined run − Single-day sum`. Zero on both products means the combined run is literally the concatenation of three independent days — positions do not carry across.

## Why drift delta is exactly zero

Inspected `prosperity4bt/runner.py:355-364`:

```python
state = TradingState(
    traderData=trader_data,
    timestamp=0,
    listings={},
    order_depths={},
    own_trades={},
    market_trades={},
    position={},          # ← fresh empty dict per day
    observations=Observation({}, {}),
)
```

The runner constructs a new `TradingState` with `position={}` at the start of every day inside a multi-day run. Our strategy cannot hold inventory across day boundaries even if it wanted to — the runner gives it an empty position dict on day −1 t=0 regardless of what it did on day −2.

Position trajectory extraction from the combined log was therefore skipped as redundant — single-day reproduction is a stronger proof than log parsing.

## Decision tree application

Per the plan:

> If `Drift delta` for Pepper is < 10k → Strategy is real MM. No changes needed. Proceed to Sprint 2 as planned.

Delta is 0. **Proceed to Sprint 2 as planned.** No day-boundary flattening needed. Do not modify Pepper.

## Remaining concerns (not drift-related)

These are flagged for Sprint 2 (visualizer) rather than blocking submission:

1. **Pepper day −1 = 47,228 is a 10× outlier** vs. days −2 (4,298) and 0 (7,286). It is genuine single-day PnL, not drift carry. Hypotheses to eyeball on the visualizer:
   - Day −1's intra-day path happens to oscillate more densely within its ±500 band → more MM round-trips.
   - The interaction of our `PEPPER_BAND_WIDTH` + `PEPPER_MIN_EDGE` with day −1's specific volatility profile was favorable.
   - Some trade or counterparty flow pattern specific to that day.

2. **Total 101k vs. Discord ceiling of ~10k for basic MM.** Possible explanations, in descending order of likelihood:
   - Practice bots are more generous than live (no informed flow).
   - `--match-trades all` (default) is an optimistic fill model — the backtester fills us on any market trade at a price equal-to-or-worse than our quote, which overestimates passive fill rate.
   - Our specific quote geometry exploits a practice-data quirk.

   The second is the single most likely lever. Sprint 4's `--match-trades worse` re-run is the right test for this.

## Recommendation

- **Submit v1 as-is.** The drift hypothesis is falsified. No Pepper modifications are warranted at this stage.
- **Sprint 2 unchanged:** upload `logs/run_20260416_233201.log` to the visualizer; check that quote placement, fill rate, and position trajectory look like genuine MM.
- **Sprint 4 includes** a `--match-trades worse` re-run — that is the better stress test for the "101k is optimistic backtester matching" concern.

## One-sentence interpretation

The practice data was teaching us that our MM strategy extracts 4k–47k of intra-day Pepper PnL depending on that day's random path, and the combined 101k is a clean sum of three independent days rather than an anchor-drift artifact.
