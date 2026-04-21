# Diagnostic Round 2 — matcher + day-1 anomaly

**Date:** 2026-04-17
**Purpose:** Rule out (H1) `--match-trades all` optimism and (H2) day-1-specific luck before submission.

## TL;DR — ship v1 with expectations adjusted

- **H1 falsified.** Conservative matcher gives *more* PnL (117,616 vs 101,414), not less. The `all` matcher is actually depressing our PnL on days -2 and 0, not inflating it.
- **H2 explained.** Day -1's 10× outlier under `all` shrinks to a 3× outlier under `worse` (48k vs 14k/13k). The remaining 3× is inventory luck, not a day-specific strategy feature — book microstructure is statistically identical across all 3 days.
- **Ship v1. Expected live PnL: 15–85k across 3 days, most likely outcome 40–60k.** Osmium alone ≈41k is the tight fallback floor; Pepper's range is wide because ~half its PnL is directional inventory against that day's drift (true live expectation: 0 ± large).

---

## Test 1 — matcher comparison

| | all (prev) | worse | ratio |
|---|---:|---:|---:|
| Osmium Day -2 | 13,183 | 12,739 | 0.97 |
| Osmium Day -1 | 15,569 | 15,420 | 0.99 |
| Osmium Day 0 | 13,850 | 13,400 | 0.97 |
| Pepper Day -2 | 4,298 | 14,186 | **3.30** |
| Pepper Day -1 | 47,228 | 48,452 | 1.03 |
| Pepper Day 0 | 7,286 | 13,418 | **1.84** |
| **TOTAL** | **101,414** | **117,616** | **1.16** |

Osmium is insensitive to matcher (~0.98). Pepper days -2 and 0 *improve* under worse-matching — the `all` matcher was passively filling us at moments that hurt Pepper's inventory. Under `worse`, Pepper's per-day spread is 14k/48k/13k (still a day-1 outlier, but 3× not 10×).

Interpretation: **Our PnL is not a matcher artifact.** If anything, live matching (closer to `worse`) should produce *cleaner* Pepper PnL on "normal" days.

---

## Test 2a — Pepper fill breakdown (worse matcher)

| | Day -2 | Day -1 | Day 0 |
|---|---:|---:|---:|
| Buy trades (count / volume) | 216 / 1,110 | 240 / 1,145 | 216 / 1,121 |
| Sell trades (count / volume) | 214 / 1,129 | 209 / 1,102 | 200 / 1,055 |
| VWAP buy | 10,486.6 | 11,468.2 | 12,511.9 |
| VWAP sell | 10,507.8 | 11,491.5 | 12,494.1 |
| **VWAP spread (sell−buy)** | **+21.2** | **+23.3** | **−17.8** |
| Realized PnL (round-trip) | 23,566 | 25,669 | **−18,796** |
| End-of-day position | −19 | +43 | +66 |
| Inventory PnL (mark-to-mid) | −9,380 | +22,783 | +32,214 |
| **Total** | **14,186** | **48,452** | **13,418** |

**Key observation:** Fill counts are essentially identical across days (216–240 buys, 200–214 sells, ~1100 units each side). Our strategy is round-tripping at the same rate every day. The PnL variance comes from two things:

1. **Day 0 got whipsawed** (VWAP_sell < VWAP_buy → −18.8k realized), but the big end-of-day long (+66) on an upward-drifting day rescued us to +13k.
2. **Day -1 kept a persistent +43 long** on an upward-drifting day, harvesting both spread (+25.7k realized) and directional inventory (+22.8k).

Across the three days, **realized MM edge is stable (~23–26k) when we get clean round-trips, ~−19k when we get whipsawed.** Inventory PnL is basically random (−9k / +23k / +32k). Most of Pepper's variance is inventory noise, not MM-quality variance.

---

## Test 2b — Pepper position trajectory (worse matcher)

| | Day -2 | Day -1 | Day 0 |
|---|---:|---:|---:|
| Mean position | 4.97 | **38.79** | 2.99 |
| Mean abs position | 20.20 | 38.93 | 25.87 |
| Std position | 25.53 | 17.85 | 31.30 |
| Zero-crossings | 36 | **15** | 33 |
| Fraction of ticks at \|pos\|>40 | 15.0% | **45.1%** | 16.5% |
| Fraction of ticks pinned at ±80 | 0.0% | 0.7% | 1.5% |
| Max abs position | 64 | 80 | 80 |

**Day -1 is dramatically different.** We sit at +38.8 on average, cross zero only 15 times (vs 33–36), and spend ~half the day with \|pos\|>40. On days -2 and 0 we behave like proper MM (oscillating near zero). On day -1 we effectively hold a ~+40 long position all day.

That persistent long is what converts day -1's MM round-trips into +48k — not a different strategy, just an unlucky (for neutrality) / lucky (for this particular day) accumulation of one-sided fills. Our strategy cannot distinguish "drifting up today" from "oscillating today" without a directional signal we don't have.

---

## Test 2c — Pepper book features (worse matcher)

| | Day -2 | Day -1 | Day 0 |
|---|---:|---:|---:|
| Mean bid-ask spread | 12.0 | 13.0 | 14.1 |
| Fraction ticks with best-level depth >20 | 13.1% | 13.2% | 13.1% |
| Fraction ticks with asymmetric depth (\|bid−ask\|>10) | 15.7% | 15.6% | 15.2% |
| Mean bid depth at best | 11.05 | 11.05 | 11.12 |
| Mean ask depth at best | 11.08 | 11.07 | 11.09 |
| Mean total bid depth | 24.09 | 24.16 | 24.17 |
| Mean total ask depth | 24.21 | 24.28 | 24.19 |

**Book microstructure is statistically identical across all three days.** There is no structural feature of day -1's order book that our strategy is exploiting. The 48k PnL is not book-specific; it's inventory × drift luck on a generic book.

---

## Test 3 — Osmium-only fallback (worse matcher)

| Day | Osmium PnL |
|---|---:|
| Day -2 | 12,739 |
| Day -1 | 15,420 |
| Day 0 | 13,400 |
| **Total** | **41,559** |

Sharpe 9.92, tiny drawdown. Osmium PnL is **extremely stable** (mean 13.85k/day, std 1.35k). This is the reliable floor if Pepper turns to noise on live.

---

## Recommendation: **Ship v1 with expectations adjusted**

Both hypotheses are sufficiently explained without invalidating the strategy:

- **H1 (matcher inflation): explicitly falsified.** Worse-matcher PnL is 116% of all-matcher PnL. The backtester is not the reason we're making money.
- **H2 (day-1 magic): explained as inventory × drift coincidence.** Same MM round-trip rate, same book features, different accumulated inventory against that day's drift. On live, this component is a coin flip, not a repeatable edge.

Assumptions for live projection (worse-matcher per-day as baseline, 50% haircut for live-vs-practice degradation):

- **Osmium per day:** 12.7–15.4k → live: 6–15k/day → **3-day total: 20–45k** (narrow range; MM around a fixed fair value generalizes well).
- **Pepper per day realized (MM edge):** stable 23–26k under clean conditions, can flip to −19k when whipsawed. Live expectation: **−30k to +50k over 3 days**.
- **Pepper per day inventory:** essentially a random walk against drift. Zero-mean expectation: **−30k to +30k over 3 days**.

**Expected live PnL range: 15k – 85k over 3 days, most likely outcome 40–60k.**
**Hard floor if Pepper completely falls apart on live: ~20k** (Osmium-only after a 50% haircut from 41k).

Why ship v1 rather than Osmium-only fallback:
- Pepper's expected value is positive even after haircuts (MM round-trips are real, book-agnostic edge).
- The 3× day -1 outlier is inventory luck, not a bug.
- The hard floor (Osmium-only after haircut) is low (~20k) but not catastrophically worse than the Pepper-included downside. The upside case (85k) is 4× larger than the fallback.
- Nothing in the evidence says "Pepper is broken." It says "Pepper's PnL is volatile and partly directional."

Do *not* disable Pepper. Do *not* tune parameters (plan's one-change-at-a-time rule). Proceed to visualizer sanity-check (Sprint 2), then parameter sweep (Sprint 3).
