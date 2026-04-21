# R2 vs R1 baseline comparison (Pepper-focused)

**Sprint:** Sprint 3 (regime diagnostic)
**Date:** 2026-04-20
**Script:** `analysis/r2_diagnostic.py` (reproducible — rerun any time)
**Canonical logs:**
- R1 practice (3 days merged, worse matcher, wall_vol=12): `backtests/2026-04-20_01-11-43.log`
- R2 practice (3 days merged, worse matcher, wall_vol=12): `backtests/2026-04-20_01-11-55.log`

**Pepper PnL context** (cumulative at end of each merged-mode day):

| Round | Day | Pepper cum PnL | Day delta |
|---|---:|---:|---:|
| R1 | -2 | +17,431 | +17,431 |
| R1 | -1 | +93,614 | **+76,183** (big win) |
| R1 | 0  | +113,623 | +20,009 |
| R2 | -1 | +3,329 | +3,329 |
| R2 | 0  | −15,294 | **−18,623** (worst) |
| R2 | 1  | −17,876.5 | −2,582.5 |

---

## Data hygiene note

Each day has 13–22 ticks where the source CSV writes `mid_price = 0.0` because
both sides of the book are empty. The live strategy sits out on such ticks
(no orders emitted). All statistics below exclude those degenerate ticks —
without filtering, they inflated Pepper std by ~220 and max-drawup by ~10,000
and produced nonsense comparisons. Filter: `mid_price > 1`.

The filtering is symmetric across R1 and R2 (not an R2-specific correction).

---

## Task 1 — Baseline per (round, day, product)

| Round | Day | Product | Ticks | Mean | Std | Drift | Spread_med | Spread_p75 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| R1 | -2 | Osmium | 9,982 | 9,998.2 | 5.2 | -16 | 16 | 18 |
| R1 | -2 | Pepper | 9,984 | 10,500.0 | **288.7** | **+1,003** | 12 | 14 |
| R1 | -1 | Osmium | 9,983 | 10,000.8 | 4.5 | -1 | 16 | 18 |
| R1 | -1 | Pepper | 9,983 | 11,500.0 | **288.6** | **+1,000** | 13 | 15 |
| R1 | 0  | Osmium | 9,986 | 10,001.6 | 5.7 | -6 | 16 | 18 |
| R1 | 0  | Pepper | 9,979 | 12,500.2 | **288.7** | **+1,002** | 14 | 16 |
| R2 | -1 | Osmium | 9,985 | 10,000.8 | 4.5 | +11 | 16 | 18 |
| R2 | -1 | Pepper | 9,987 | 11,500.1 | **288.6** | **+998** | 13 | 15 |
| R2 | 0  | Osmium | 9,984 | 10,001.6 | 5.7 | +5 | 16 | 18 |
| R2 | 0  | Pepper | 9,982 | 12,499.9 | **288.6** | **+1,002** | 14 | 16 |
| R2 | 1  | Osmium | 9,978 | 10,000.2 | 5.0 | -15 | 16 | 18 |
| R2 | 1  | Pepper | 9,984 | 13,500.1 | **288.7** | **+1,000** | 15 | 17 |

### Headline findings

1. **Pepper price dynamics are essentially identical across R1 and R2.**
   Every day — winner or loser, R1 or R2 — shows +1000 net drift and a std
   of 288.6–288.7. The std identity to 3 significant figures is not an accident:
   it is the variance of a near-linear +1000 ramp over 10,000 ticks, which
   recurs deterministically.

2. **Pepper mid-price ladders up by exactly 1,000 each day.** R1 days anchor at
   10,500 / 11,500 / 12,500. R2 days anchor at 11,500 / 12,500 / 13,500. The
   +1 tick spread widening per day tier is the only systematic R2-vs-R1
   difference in this table.

3. **Osmium baseline is stable and symmetric across rounds.** std 4.5–5.7,
   drift within ±20 on every day. Osmium PnL (+41k on R1, +48k on R2)
   confirms the Osmium environment did not change; Osmium's strategy works
   the same way in both regimes.

Spread widens by 1 tick from R1 to R2 at each Pepper price tier (12→13, 13→14,
14→15). This is a real but small delta — unlikely by itself to drive −18k on
a single day.

---

## Task 2 — Intra-day drift characterization (Pepper)

Rolling-mean window = 500 ticks. A tick counts as "up" if `mid − rolling_mean > 1`,
"down" if `< −1`, "flat" otherwise. Direction flips = transitions between +1
and −1 bias (zero runs between are ignored).

| Round | Day | NetDrift | Up% | Down% | Flat% | DirFlips | MaxDrawup | MaxDrawdown |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R1 | -2 | +1,003 | 99.7 | 0.1 | 0.2 | 10 | +1,004.5 | -17.0 |
| R1 | -1 | +1,000 | 99.7 | 0.1 | 0.2 | 20 | +1,011.0 | -19.0 |
| R1 | 0  | +1,002 | 99.8 | 0.1 | 0.1 | 15 | +1,013.0 | -20.0 |
| R2 | -1 | +998   | 99.6 | 0.1 | 0.2 | 14 | +1,003.5 | -17.0 |
| R2 | 0  | +1,002 | 99.6 | 0.1 | 0.3 | 18 | +1,012.0 | -20.0 |
| R2 | 1  | +1,000 | 99.7 | 0.1 | 0.2 | 13 | +1,008.0 | -21.0 |

### Interpretation

- Pepper drifts monotonically upward on **all six days**. The fraction of
  ticks above the rolling mean is 99.6–99.8% on every day; the fraction below
  is 0.1%.
- Max intra-day drawdown from a running peak is capped at −17 to −21 ticks on
  every day. No day shows a sustained reversal.
- Direction-flip counts (10–20) are in the same range across R1 and R2; R2
  losing days (d0=18, d1=13) are not noticeably choppier than R1 winning
  days (d-2=10, d-1=20, d0=15).

**Hypothesis H2 (intra-day reversal regime differs) is not supported by the data.**

---

## Task 3 — EMA signal replay (α=0.005, threshold=8.0)

Replay of the exact overlay in `algo/strategies/pepper_root.py`, fed by each
day's `mid_price` series. Counts of ticks where the signal magnitude exceeds
the bias threshold, and whether the triggered bias is long (+) or short (−).

| Round | Day | Threshold_hit% | Pos% | Neg% | AvgDuration | SignFlips |
|---|---:|---:|---:|---:|---:|---:|
| R1 | -2 | 99.1 | 100.0 | 0.0 | 760.9 | 0 |
| R1 | -1 | 99.0 | 100.0 | 0.0 | 494.3 | 0 |
| R1 | 0  | 99.1 | 100.0 | 0.0 | 412.0 | 0 |
| R2 | -1 | 98.8 | 100.0 | 0.0 | 657.9 | 0 |
| R2 | 0  | 99.1 | 100.0 | 0.0 | 581.8 | 0 |
| R2 | 1  | 98.9 | 100.0 | 0.0 | 581.1 | 0 |

### Interpretation

- The EMA overlay fires on ~99% of ticks on every day, R1 and R2 alike.
- The overlay's direction is **always long** (pos%=100, sign_flips=0) on
  every day — which makes sense mechanically: a +1000 monotone drift keeps
  the price consistently above its lagged EMA.
- AvgDuration (runs of continuous long bias) is comparable across rounds;
  R2 losing days are in the middle of the R1 range.

**Hypothesis H6 (EMA threshold miscalibrated for R2) is not supported.**
The overlay behaves identically in both rounds. Whatever goes wrong on
R2 days 0 and 1, it is not that the overlay fires differently.

Side note: this replay uses a per-day reset (each CSV starts with a fresh
EMA). The production strategy resets on `state.timestamp == 0`, which in
merged-backtest mode fires only at the very start of day −1 — meaning the
EMA actually carries over across days in merged backtests. That asymmetry
between backtest and live is worth flagging as a separate issue, but it
does not change this diagnostic: the overlay triggers almost identically
regardless.

---

## Task 4 — Per-trade PnL decomposition (Pepper)

Extracted from the merged backtest logs, windowed to each day. Realized PnL
= (VWAP_sell − VWAP_buy) × min(buy_vol, sell_vol); inventory PnL =
end_position × (end_mid − VWAP on the long/short side).

| Round | Day | Buys | Sells | BuyVol | SellVol | VWAP_buy | VWAP_sell | **VWAP_spread** | Realized | EndPos | InvPnL | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R1 | -1 | 150 | 126 | 727 | 656 | 11,415.9 | 11,469.0 | **+53.13** | **+34,854** | +71 | +41,329 | **+76,183** |
| R2 | -1 | 231 | 237 | 1,218 | 1,228 | 11,520.0 | 11,526.6 | **+6.62** | +8,058 | -10 | -4,729 | +3,329 |
| R2 | 0  | 211 | 228 | 1,095 | 1,109 | 12,536.9 | 12,525.9 | **−10.95** | **−11,986** | -14 | -6,637 | **−18,623** |
| R2 | 1  | 227 | 232 | 1,186 | 1,161 | 13,535.5 | 13,523.2 | **−12.22** | **−14,183** | +25 | +11,601 | -2,583 |

### Smoking gun

**VWAP_sell − VWAP_buy** is the single per-unit edge our market-making captures.
It flips sign between R1 and R2 losing days:

- R1 day -1 (big winner): **+53 ticks per round-trip.** We sell at prices that
  are, on average, 53 ticks above the prices we bought at.
- R2 day 0 (worst loser): **−11 ticks per round-trip.** We sell at prices
  below where we bought. This is the opposite of market-making.
- R2 day 1 (loser): **−12 ticks per round-trip.** Same pattern.
- R2 day -1 (small winner): **+7 ticks per round-trip.** Barely positive.

### Volume context

Trade count and volume on R2 are **~1.5× to 1.7× R1**:

| Day | Buy fills | Sell fills | Total volume |
|---|---:|---:|---:|
| R1 -1 (+76k) | 150 | 126 | 1,383 |
| R2 -1 (+3k) | 231 | 237 | 2,446 |
| R2 0 (-19k) | 211 | 228 | 2,204 |
| R2 1 (-3k) | 227 | 232 | 2,347 |

R2 runs ~1.6× as many fills per day. Combined with a negative VWAP_spread,
higher volume magnifies the loss. (Counterparty-trade count in the raw
trades CSV is ~330/day on every day, so the increase is in the share of
counterparty flow that hits our quotes, not in total market activity.)

### What this means

The MM edge that won +53 ticks/round-trip on R1 day -1 now captures −11 to
−12 ticks/round-trip on R2 losing days. That is not a drift issue, a
threshold issue, or a volatility issue — the price path is identical.
It is a **fill-distribution issue**: our passive quotes are being filled at
systematically unfavorable prices in R2.

This is the classical definition of adverse selection: informed counterparties
execute against stale quotes while uninformed counterparties trade in-between.
The strategy is structurally well-suited for uninformed noise (which R1
provided in abundance) and structurally ill-suited for informed flow.

See `round2_pepper_diagnosis.md` for the hypothesis scorecard and
intervention candidates.
