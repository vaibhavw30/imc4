# Round 1 — Dataset Insights & Strategy Implications

**Status:** Snapshot after initial scaffolding + EDA. Update this doc as new findings emerge.
**Source data:** `data/prices_round_1_day_{-2,-1,0}.csv`, `data/trades_round_1_day_{-2,-1,0}.csv`
**Reproduce:** `python -m analysis.explore` (writes plots to `analysis/plots/`)

---

## 1. Purpose

This document captures everything we currently know about Round 1's two products, the data we have for them, and the implications for our trading model. It exists so that:

- Future-us (after a context wipe or a few days away) can re-orient quickly.
- Strategy parameter changes are tied back to evidence, not gut feel.
- We avoid re-discovering the same data-quality gotchas mid-iteration.

If a finding here turns out wrong, *update or delete the section* — don't add a contradicting one alongside.

---

## 2. Dataset structure

### Prices files (`data/prices_round_1_day_*.csv`)

| Property | Value |
|---|---|
| Days available | -2, -1, 0 (three pre-competition practice days) |
| Rows per day | 20,000 (10,000 timestamps × 2 products) |
| Unique timestamps per day | 10,000 |
| Timestamp range per day | 0 .. 999,900 |
| Timestamp step | 100 (so 1 "tick" = 100 timestamp units) |
| Products | `ASH_COATED_OSMIUM`, `INTARIAN_PEPPER_ROOT` |
| Separator | `;` (semicolon, not comma) |

Each row is one (product, timestamp) snapshot of the order book with up to **3 price levels per side**:

```
day; timestamp; product;
bid_price_1; bid_volume_1; bid_price_2; bid_volume_2; bid_price_3; bid_volume_3;
ask_price_1; ask_volume_1; ask_price_2; ask_volume_2; ask_price_3; ask_volume_3;
mid_price; profit_and_loss
```

`mid_price` is `(bid_price_1 + ask_price_1) / 2` when both sides exist, falling back to whichever side is present. `profit_and_loss` is the running PnL of the *bot trader* that produced the file (not us) — it's a useful baseline to beat.

### Trades files (`data/trades_round_1_day_*.csv`)

| Property | Value |
|---|---|
| Trades per day | ~750 (760 day -1, 743 day 0, 773 day -2) |
| Columns | `timestamp; buyer; seller; symbol; currency; price; quantity` |
| Currency | `XIRECS` (the Prosperity 4 unit; replaces P3's `SEASHELLS`) |
| `buyer` / `seller` columns | **All NaN** — counterparties are anonymized |

**This is a meaningful change from Prosperity 3**, where some products had named bots (e.g. "Olivia" telegraphed direction in ORCHIDS). For Round 1 we can't identify the counterparty, so any "follow-the-bot" strategy is off the table.

We currently load trades via `analysis.load_data.load_trades` but **do not analyze them in `explore.py` yet** — see §11 (Future work).

---

## 3. Data quality: the `mid_price = 0` gotcha

**Problem.** ~50 rows per product per file have **both** `bid_price_1` and `ask_price_1` as `NaN` (empty book on both sides). For these rows, the CSV writes `mid_price = 0.0` rather than `NaN`.

**Why it matters.** A naive `df["mid_price"].dropna()` does not filter these out. They poison every downstream statistic:

- **Mean shifts down** by ~17 (OSMIUM) or hundreds (PEPPER) vs. the median.
- **Std explodes** to 400+ (OSMIUM) or 1000+ (PEPPER) when the real value is single-digit (OSMIUM) or ~289 within-day (PEPPER).
- **Lag-1 return autocorr is forced to exactly −0.5**, regardless of the underlying process. This is the most insidious symptom — it's a real number that *looks like* a strong mean-reversion signal.

**The −0.5 autocorr math.** A spike-and-recover pair `(price → 0 → price)` produces consecutive returns `(−L, +L)`. Each pair contributes `−L²` to the lag-1 covariance and `2L²` to the variance. Ratio = exactly **−0.5**. Even ~50 such pairs out of 30,000 rows are large enough (`L ≈ 10,000`) to dominate both sums. **If you see lag-1 autocorr near −0.5 across multiple products, suspect outliers before celebrating mean-reversion.**

**Fix (already applied in `analysis/explore.py`).** Filter `mid_price > 0` and `mid_price.notna()` via `_clean_valid()`. Compute returns *within each day* (don't `.diff()` across day boundaries — it produces one extra spurious return per day boundary).

**Implication for the live bot.** The same condition (empty book) will occur during the actual competition. Both strategies handle it: they `return []` if the order book is empty or `wall_mid` returns `None`. Verify in the visualizer that we never quote into a phantom 0-price book.

---

## 4. `ASH_COATED_OSMIUM` — STABLE (Resin analog)

### Numbers (after cleaning)

| Stat | Value |
|---|---|
| Valid rows (after dropping empty-book) | 29,951 / 30,000 |
| Mean mid | **10,000.20** |
| Std mid (overall) | 5.35 |
| Per-day std | 5.22 / 4.45 / 5.68 (days -2 / -1 / 0) |
| Per-day mean | 9,998.2 / 10,000.8 / 10,001.6 |
| Day-to-day mean drift | 3.4 ticks (negligible) |
| Min / median / max | 9,977 / 10,000.5 / 10,023 |
| p1 / p99 | 9,987 / 10,013 (98% within ±13) |
| Mode (rounded int) | **10,002** (appears 10.3% of ticks) |
| Bid-ask spread | mean 16.18, median 16, max 22 |
| Lag-1 return autocorr | **−0.495** (real, not artifact) |
| Lag-5 / lag-10 autocorr | −0.005 / −0.006 (zero) |
| Rolling 100-tick std | mean 2.87, max 4.47 |

### Interpretation

OSMIUM behaves exactly like Prosperity 3's **RAINFOREST_RESIN**: a fixed integer fair value at **10,000** with tiny noise around it. Day-to-day drift is essentially zero (3.4 ticks across two practice days). The price is half-integer (because mid = (bid+ask)/2 with integer prices and even-tick spreads), which is why no single rounded value captures more than 10% of ticks even though the distribution is extremely tight.

The **mode being 10,002 rather than 10,000** is misleading — it's an artifact of rounding half-integers. The *true* anchor is 10,000 (matches mean to 0.20 ticks). Stick with `OSMIUM_FAIR_VALUE = 10_000`.

The lag-1 autocorr of **−0.50** is **real** (it survives cleaning) and reflects genuine tick-by-tick mean-reversion: when OSMIUM ticks up, it tends to tick back down on the next print. This is the ideal regime for a market maker — every fill earns spread *plus* the expected mean-revert move.

### What's surprising

**The bid-ask spread is huge (16 ticks) relative to the price's variance (std 5).** That means the inside book sits well outside fair value, and *even quoting one tick away from fair* (`fair ± 1`) puts us deep inside the spread with significant adverse-selection protection. We could reasonably quote at `fair ± 2` or `fair ± 3` and still be inside the book on most ticks, capturing more edge per fill.

### Strategy parameter implications

Current values in `algo/strategies/osmium.py`:

| Constant | Current | Evidence-based recommendation |
|---|---|---|
| `OSMIUM_FAIR_VALUE` | 10000 | ✅ Confirmed |
| `OSMIUM_POSITION_LIMIT` | 80 | ⚠ From `sample.py`; verify against problem statement |
| `OSMIUM_MAKE_EDGE` | 1 | Try **2 or 3** in backtest — wide spread allows it |
| `OSMIUM_BASE_QUOTE_SIZE` | 20 | Backtest first; with limit 80, this fills aggressively |

**Take logic** (`ask_price < fair_value`) currently has zero deadband — we lift any sub-fair ask. Given the wide spread that's probably correct, but consider an asymmetric edge: take harder when far from limit, lighter when near it.

---

## 5. `INTARIAN_PEPPER_ROOT` — DAY-ANCHORED (NOT a Kelp random walk)

### Numbers (after cleaning)

| Stat | Value |
|---|---|
| Valid rows | 29,946 / 30,000 |
| Mean mid (overall) | 11,499.89 |
| Std mid (overall) | 866.11 |
| **Per-day mean** | **10,500.0 / 11,500.0 / 12,500.2** (days -2 / -1 / 0) |
| **Per-day std** | **288.72 / 288.67 / 288.73** |
| Day-to-day mean drift | 2,000.21 ticks |
| Min / median / max | 9,998 / 11,500.0 / 13,007 |
| p1 / p99 | 10,029.5 / 12,969.0 (range = 2,939.5) |
| Bid-ask spread | mean 13.05, median 13, max 21 |
| Lag-1 return autocorr | **−0.501** |
| Lag-5 / lag-10 autocorr | +0.004 / +0.005 (zero) |
| Rolling 100-tick std | mean 3.64, max 4.79 |

### The smoking gun

**Per-day means are 10,500 / 11,500 / 12,500 — exactly 1,000 apart, in arithmetic progression.**

**Per-day stds are 288.72 / 288.67 / 288.73 — essentially identical, all ≈ 1000/√12 = 288.68.**

That standard deviation is the **exact theoretical std of a continuous uniform distribution on a width-1000 interval**. Combined with the median sitting *exactly* at the day's anchor and the percentiles being *symmetric around the anchor* (p25→anchor = anchor→p75 = 750; p1→anchor = anchor→p99 ≈ 1470), the data is consistent with PEPPER's mid-price being **uniformly distributed on `[anchor − 500, anchor + 500]` within each day** (with light tails extending to about ±1500).

This is **not** a random-walk Kelp analog. Possibilities:

1. **Deterministic daily anchor** that increments by a fixed amount day-over-day (10,500 → 11,500 → 12,500 → 13,500?). This would be a *huge* exploit if true — we'd know fair value with certainty at competition time.
2. **Coincidence over 3 days.** Three samples is too few to rule out chance, especially given Prosperity's tendency to use "clean" round numbers.
3. **Mean-reverting wave around a slow daily drift.** The price could be a smooth signal (e.g. triangle/sine) that visits each value in [anchor−500, anchor+500] roughly uniformly, plus tick-level noise. The lag-1 autocorr of −0.50 with intra-day std of 289 would fit this — the smooth signal explains the wide range, the tick noise explains the autocorr.

**We cannot distinguish (1) from (3) without competition-day data.** Action: design the strategy to *adapt* (compute anchor on the fly via wall_mid or a long EMA of mid) rather than assume the +1000/day pattern continues.

### Interpretation for strategy

The current `PepperRootStrategy` already uses `wall_mid` (recomputed each tick), which adapts to whatever the day's anchor turns out to be. **No code change needed if interpretation (1) or (3) holds.** What might need tuning:

- **`PEPPER_BAND_WIDTH`** — currently 1. With intra-day std of 289 and price uniformly bouncing across a 1,000-tick range, a fair-derived bid_quote of `fair − 1` is very close to fair. That's fine if we trust `wall_mid`; if we don't, widen.
- **`PEPPER_MIN_EDGE`** — currently 2. If the autocorr-driven mean-revert is real, even small edges are profitable; consider lowering to 1 in a backtest variant.
- **`PEPPER_WALL_VOLUME = 15`** — heuristic threshold for "designated MM" quotes. We haven't yet verified that PEPPER's book actually has fat-volume levels at all. If it doesn't, `wall_mid` falls through to plain `mid_price`, which is fine for a uniform-around-anchor process but loses the noise-filtering benefit. **Action item:** print `wall_mid vs. mid_price` in a backtest run and check how often they diverge.

### What about that lag-1 autocorr of −0.50?

It's the same value as OSMIUM. Two products having identically strong tick-level mean-reversion is consistent with both being "anchor + tick-noise" processes with the same noise structure. It's *not* an artifact this time (we cleaned the data). It means: market making PEPPER inside a tight quote band should systematically capture spread + reversion edge, the same way it does for OSMIUM — *as long as we have the anchor right*.

### Risk specific to PEPPER

If interpretation (3) is correct (smooth slow signal + tick noise), then a sustained directional move could push us through our position limit before `wall_mid` adapts. The inventory-widening band (`PEPPER_MAX_EXTRA_BAND`) is the safety valve, but it's untuned. Watch position-over-time in the visualizer for runaway accumulation.

---

## 6. Cross-product observations

| Property | OSMIUM | PEPPER |
|---|---|---|
| Regime | Stable (fixed FV) | Day-anchored (FV unknown live) |
| Within-day std | 5.4 | 288.7 |
| Day-to-day FV drift | 3 | ~1000 |
| Bid-ask spread (median) | 16 | 13 |
| Lag-1 autocorr | −0.495 | −0.501 |
| Lag-5+ autocorr | ~0 | ~0 |
| Empty-book ticks/day | ~16 | ~18 |

**Both products have wide spreads relative to their per-tick variance.** This is fundamentally different from real-world equity markets where spreads are ~1 tick wide and you fight for queue position. Here we fight for *edge*, not queue. Aggressive mid-price-anchored quoting is the right move on both products.

**Both have strong tick-level mean-reversion.** This is the signal we want — a market maker's expected PnL per fill is `spread/2 + |reversion|`, which compounds on every round trip. The `−0.5` autocorr roughly says: of a 1-tick deviation, about half tends to reverse on the next tick.

**Neither product reacts to lag-5+ history.** The mean-revert is short-lived, so don't bother with 5-tick or 10-tick momentum/reversal signals.

---

## 7. The wall_mid theory and when it applies

`algo/utils/order_book.py:wall_mid` finds the deepest level on each side (size ≥ `min_volume`) and returns the midpoint. Theory: designated market makers post fat quotes near fair value; thin top-of-book quotes are noise.

**For OSMIUM:** we don't currently use it (we hardcode fair = 10,000). That's correct — when fair value is fixed, no live estimation is needed.

**For PEPPER:** we rely on it. **Open question:** does PEPPER's book actually have wall-volume quotes? We haven't verified. Two failure modes:

- **No fat quotes ever.** `wall_mid` always falls back to plain `mid_price`. Strategy still works but loses noise-filter benefit.
- **Fat quotes exist but mislead** (e.g., a stale level deep in the book). `wall_mid` returns a wrong anchor, our quotes drift away from real fair, we lose money.

Add a one-line `logger.print` in `pepper_root.py` showing `wall_mid` vs `mid_price` and inspect the visualizer to confirm.

---

## 8. Strategy implications — concrete

### Things confirmed by EDA
- `OSMIUM_FAIR_VALUE = 10_000` — keep.
- Wide spreads on both products → aggressive in-quoting is safe.
- Mean-reversion is real on both → market making is +EV before fees.

### Things to change after first backtest
- `OSMIUM_MAKE_EDGE`: try 2 and 3. Wider edge → fewer fills, more PnL/fill. Find the knee.
- `OSMIUM_BASE_QUOTE_SIZE`: confirm 20 doesn't push us through limit-80 in a few ticks.
- `PEPPER_MIN_EDGE`: try 1 (more aggressive) and 3 (more passive). Compare PnL.
- Add `wall_mid vs. mid_price` debug print to `pepper_root.py`.

### Things to do before submitting
- Verify position limit = 80 against the **official Round 1 problem statement** (not just sample.py).
- Calibrate `OSMIUM_MAKE_EDGE` on all three days; require positive PnL on each.
- Flatten to single-file `trader.py` (see §11).

### Things NOT to do
- Don't build a momentum signal. Lag-5+ autocorr is zero on both products.
- Don't try to identify the counterparty. Trades are anonymized in P4.
- Don't hardcode PEPPER's anchor as 10,500 + 1000·day. Three days isn't enough confirmation.
- Don't over-engineer the empty-book handler. Returning `[]` for that tick is correct and frequent enough not to matter.

---

## 9. Trades file: what we know and don't

We've loaded `data/trades_round_1_day_*.csv` but not analyzed it. Quick observations from a head-3 read:

- Day -2 OSMIUM trades around 9985–9998 → consistent with fair ≈ 10,000.
- Day -1 PEPPER trades around 10,995–10,999 → consistent with day -1 anchor = 11,500 (these are below anchor).
- Day 0 PEPPER trades at 11,998–12,010 → consistent with day 0 anchor = 12,500.
- Currency is `XIRECS` (P4-renamed; was `SEASHELLS` in P3).
- All `buyer` and `seller` fields are `NaN` — anonymized.

**What we'd do with this data later:**
- Trade frequency at each price level → reveals where actual liquidity sits (vs. resting orders).
- Volume-weighted average trade price per window → alternative fair-value estimator.
- Asymmetry: are buys at the ask happening more than sells at the bid? Could indicate directional bot pressure.

**Action item:** add `analysis/trades_explore.py` once the price-side strategy is working.

---

## 10. Risks and open questions

| # | Question | Why it matters | How to resolve |
|---|---|---|---|
| 1 | Is PEPPER's day anchor +1000/day deterministic, or is it a 3-sample coincidence? | If deterministic, we can hardcode and dominate. If not, we must estimate live. | Wait for day 1+ data once competition starts; fall back to `wall_mid` either way. |
| 2 | Position limit 80 — confirmed in code or just in `sample.py`? | Exceeding limit cancels all our orders for that product (silent kill). | Read the official Round 1 problem statement carefully. |
| 3 | Does PEPPER's book have wall-volume quotes? | If not, `wall_mid` falls back to `mid_price`. Strategy still works but loses one layer of robustness. | Add diagnostic print, run backtest, eyeball log. |
| 4 | Does `prosperity4btest` honor `PYTHONPATH=.` for absolute imports inside `algo/trader.py`? | If not, the modular structure breaks during local backtest. | Run `./run_backtest.sh` once and see. Worst case: switch to relative imports or flatten now. |
| 5 | What's the actual pre-flatten → post-flatten diff? | We're claiming the modular and flat versions produce identical orders. We haven't verified. | Once we write `scripts/flatten.py`, diff one tick's orders between both. |
| 6 | Does the bot trader's `profit_and_loss` column give us a baseline to beat? | Yes — if we can't beat the bot's PnL on practice days, we're not ready. | Print `df.groupby('product')['profit_and_loss'].last()` per day and compare to backtest PnL. |
| 7 | Are observations (sugar, sunlight) populated in Round 1? | They're P4-specific and might unlock conversion arbitrage in later rounds. Round 1 likely empty. | Print `state.observations` in the first backtest tick. |

---

## 11. Future work

In rough priority order:

### Before submitting Round 1
1. **Run `./run_backtest.sh`** end-to-end. Check it doesn't crash, log uploads to visualizer.
2. **Calibrate `OSMIUM_MAKE_EDGE`** via grid search (1, 2, 3, 4) on all three days. Pick the knee.
3. **Verify PEPPER strategy** on the visualizer: position behavior, fill rate, no runaway accumulation.
4. **Write `scripts/flatten.py`**: concatenate `algo/logger.py`, `algo/utils/*`, `algo/strategies/*`, `algo/trader.py` into a single self-contained `dist/trader_flat.py`. Remove `from algo.* import` lines. Strip duplicate imports.
5. **Diff flat vs modular**: run both through one backtest, confirm identical orders and PnL.

### Round 2 prep (parallelizable)
6. **`analysis/trades_explore.py`**: trade-side EDA. Volume-by-price heatmap, trade size distribution, time-of-day patterns.
7. **Per-day PnL baseline**: print bot trader's `profit_and_loss` column to know what we have to beat.
8. **Investigate PEPPER intra-day shape** — is it a triangle wave, a true random walk, or sinusoidal? Plot `mid_price` for one day at high resolution. The answer changes whether we want a wider band (random walk) or a tighter band (smooth signal).

### Carry-forward across rounds
9. **Param config separation**: when constants in 2+ strategy files start moving together (e.g., all using `WALL_VOLUME = 15`), promote to `algo/config.py`. Don't do this preemptively.
10. **Cross-tick state via `traderData`**: add when we need an EMA, accumulator, or signal that spans ticks. Round 1 doesn't.
11. **Tests**: skip until strategy logic gets non-trivial (≥3 conditional branches per phase) or we hit a regression.

---

## 12. Methodology notes (how to reproduce)

### Reading this doc later

- **Numbers** in §4 and §5 came from `python -m analysis.explore` on the cleaned data. If you re-run and they differ, either (a) the data was updated (new days dropped in), or (b) the cleaning logic changed. Check `_clean_valid()` in `analysis/explore.py`.
- **Plots** are at `analysis/plots/{PRODUCT}_{kind}.png`. Regenerated on each run; not committed.
- **The classification heuristic** (§5 footer / `explore.py:main`) uses thresholds chosen post-hoc to fit *these three days*. It's likely wrong for novel products. Update thresholds when adding R2+ products.

### Data quality checklist for any new product

When a new product appears in R2+:

1. Count `mid_price == 0` and `bid_price_1.isna() & ask_price_1.isna()` rows. If > 0, the empty-book gotcha applies.
2. Check `lag-1 return autocorr`. If suspiciously close to −0.5, suspect outliers.
3. Compare per-day mean and per-day std. Identical-across-days per-day std + arithmetic per-day means = synthetic process (suspicious — investigate).
4. Compare `mid.std()` to `mid.rolling(100).std().mean()`. If overall is much larger, drift dominates noise.
5. Check `mid_price` granularity: is it integer, half-integer, or finer? Half-integer means even-tick spreads with integer prices.

### Why returns are computed within-day

`pd.concat([df1, df2]).diff()` produces one spurious value at the boundary (`df2[0] - df1[-1]`). For 3 days that's 3 spurious returns out of ~30,000 — small enough to ignore in mean/std but enough to noticeably perturb autocorrelation estimates because consecutive cross-day diffs tend to share sign with their neighbors. `groupby("day").diff()` avoids this entirely.

### Why the −0.5 autocorr was the most diagnostic outlier signal

Most outlier-effects show up in moments (mean, std). The −0.5 autocorr signature is special because:

- It's a *fixed point* of the math (ratio of two sums dominated by the same outlier pairs).
- It's *identical across products* with completely different price scales — a giveaway that the value is structural, not behavioral.
- It exists in a range (`[−1, +1]`) where humans expect noise; seeing a clean −0.50 should set off alarms even before checking the data.

If a future EDA shows two products with the same autocorr value to 3 decimals, **stop and check for shared data quality issues before drawing conclusions**.
