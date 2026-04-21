# Round 2 Pepper diagnosis

**Sprint:** Sprint 3 (pure diagnostic — no code changes)
**Date:** 2026-04-20
**Companion data:** `docs/ROUND2/r2_vs_r1_baseline.md`
**Reproducibility:** `python3 analysis/r2_diagnostic.py all`

---

## TL;DR

**Primary cause: adverse selection, not regime shift.**

R1 and R2 Pepper price series are statistically near-identical: +1000 tick
monotone drift per day, std 288.6–288.7, spread median within ±1 tick,
EMA overlay fires on 99% of ticks with unanimous long bias on every day.
What differs is the distribution of **our fills**: per-unit MM edge
collapses from +53 ticks/round-trip on the R1 big winner day (+76k) to
−11 to −12 ticks/round-trip on R2 losing days (−19k, −3k).

Our passive quotes are being picked off at unfavorable prices in R2. This
is not fixable by tuning drift-related parameters (the drift signal is the
same). Plausible interventions cluster around (a) widening quotes to reduce
fill volume when edge is negative, (b) suppressing the EMA bias under
adverse-selection conditions, or (c) adaptive sizing based on recent realized
VWAP spread. None of these is a sure thing; Sprint 4 should pick one to
test rather than committing without further evidence.

---

## Hypothesis scorecard

Evidence citations refer to tables in `r2_vs_r1_baseline.md`.

| Hypothesis | Evidence For | Evidence Against | Verdict |
|---|---|---|---|
| **H1 — Drift magnitude differs** | None observed. | Pepper net drift is +998 to +1,003 on every day in R1 and R2 (Task 1). Drift identical to 0.5% tolerance. | **Falsified.** |
| **H2 — Intra-day reversal regime changed** | Direction-flip counts on R2 d0 (18) and d1 (13) are within R1 range (10–20) (Task 2). Not qualitatively choppier. | Up-fraction 99.6–99.7% on every day. Max intra-day drawdown capped at −17 to −21 ticks on every day. No sustained reversals anywhere. | **Falsified.** |
| **H3 — Wall structure / book depth differs** | Not directly measured (requires book-depth extraction from logs). Spread median widens by +1 tick from R1 to R2 (Task 1). | Osmium runs the same wall-based strategy and is profitable on both rounds (+41k R1, +48k R2); if walls were materially unreliable, Osmium would show it too. Pepper spread shift of +1 tick is small. | **Unlikely to be primary cause.** Could still be a secondary contributor; would need book-depth histograms to rule out fully. |
| **H4 — Spread behavior changed** | Spread_med shifts: R1 12/13/14 → R2 13/14/15 (+1 tick per tier) (Task 1). | Magnitude is tiny relative to the −11 to −12 tick VWAP collapse. A 1-tick spread shift cannot produce a 64-tick swing in per-unit MM edge. | **Falsified as primary cause.** |
| **H5 — Adverse selection** | VWAP_sell − VWAP_buy: +53 (R1 winner) → −11, −12 (R2 losers) (Task 4). We sell below our buy prices on R2 losing days. Our fill volume is 1.6× R1. Counterparty-trade count in the raw CSV is ~330/day on every day, so the extra volume comes from a larger share of counterparty flow hitting our passive quotes — classical symptom of stale quotes being selected against. | None significant. | **Strongly supported — primary cause.** |
| **H6 — EMA threshold miscalibrated** | None observed. | Threshold_hit% is 99% on every day. Signal is long 100% of the time on every day. Sign-flips = 0 on every day. Overlay fires identically in R1 and R2 (Task 3). | **Falsified.** |
| **H7 (new) — EMA bias amplifies adverse selection** | The overlay adds +8 to buy size on 99% of ticks. With the drift monotonically up, this produces a structurally long inventory. On R1 the drift pays us for being long; on R2 the adverse selection eats the edge faster than the drift covers. On R2 day 0, end-of-day position is −14 (we went from biased-long to slightly short as counterparties kept unloading into our top-of-book ask) — the EMA bias did not protect us from the adverse fills. | On R2 day 1 we end +25 long and lose only −3k; on R2 d0 we end −14 short and lose −19k. The correlation between end_pos and loss magnitude is weak. | **Plausible contributor, not sole driver.** Worth testing (see Intervention 2 below). |
| **H8 (new) — Fill share increased** | Counterparty trade count is ~330/day in both rounds, but our fill count jumped from 276 (R1 d-1) to 439 (R2 d0) to 459 (R2 d1). More of counterparty flow now trades against us, not between each other. | None — this is numeric fact from Task 4 + counterparty-trades CSV count. | **Supported, likely H5 mechanism.** |

---

## Impact estimate

**What is at stake if unfixed:** The strategy loses ~18k–21k on R2 days 0
and 1 combined (R2 Pepper total is −17,876.5 across 3 days). In live
evaluation of ~1 day, the analogous loss could be anywhere from −6k to −20k
depending on which R2 practice day best matches the live regime. A live
day that looks like R2 d0 would cost ~−18k. A live day that looks like
R2 d-1 would cost ~+3k. No single R2 practice day makes +76k.

**What is on the table if fixed well:** Neutralizing the adverse selection
(getting VWAP_spread from −12 back toward +6, R2 d-1's level, without
other regressions) on R2 d0 would recover ~19k of realized PnL. Getting it
back to R1-level (+53) on R2 d0 would recover ~60k. Neither of those
numbers is a realistic ceiling — the R1 regime of uninformed counterparty
flow is almost certainly gone for Pepper in R2. A more realistic ceiling:
~+12k/day by breaking even on realized PnL and letting inventory PnL
contribute, which would lift R2 Pepper total from −18k to approximately
+18k–+25k over 3 days. Net: the potential is real but bounded; not
comparable to the R1 live +39k headline.

**What is on the table if not fixed but mitigated (sized down):** If we
reduce Pepper quote volume to 40% of current by widening min_edge, total
trade count roughly scales down linearly. Loss on R2 practice days 0+1
shrinks from −21k to ~−8k; Osmium continues unchanged. Net round-2 total
improves from +30,758 to ~+43k. This is the "give up upside, bound
downside" branch.

---

## Intervention candidates (for Sprint 4 to evaluate, NOT to pick now)

Listed with expected-direction reasoning, not committed estimates. None are
applied in this sprint.

### 1. Widen Pepper `min_edge` from 2 to 3 or 4

**Mechanism:** Take-phase threshold tightens, reducing the set of book prices
we cross. Passive quotes post further from fair, so fewer adverse fills.

**Why plausible:** If our fills are dominated by "counterparty sells right
before a small dip" events, a wider min_edge gates them out. R1 will lose
some realized PnL but R2 will lose fewer adverse-select dollars.

**Risk:** On R1 this will clip some of the +53-tick/round-trip wins. We
should expect R1 PnL to drop. Worth it only if R2 recovery exceeds R1 loss.

**Rough direction:** R2 d0 loss could shrink 30–50% (fewer fills, the
remaining fills are on cleaner pricing); R1 d-1 win could shrink 10–20%.

### 2. Reduce or disable `PEPPER_DRIFT_BIAS_SIZE` (currently 8)

**Mechanism:** The EMA overlay currently adds 8 units of extra buy size on
99% of ticks. Suppressing this means the strategy behaves as pure inventory-
widened MM with no directional bias.

**Why plausible:** On R2 losing days the bias adds fills at the upward-drift
peaks (long-bias = more aggressive buys), which is precisely where adverse
selection bites hardest. Removing it cuts ~30–40% of Pepper fill volume
without touching the make/take core.

**Risk:** On R1 big winners like d-1, the bias IS part of how we capture
the drift. Dropping it probably costs 15–25k on R1 day -1 alone. Unless
the R2 gain exceeds this, we're trading a sure loss for an uncertain gain.

**Rough direction:** Could recover 5–15k on R2 d0+d1, but may sacrifice
20–40k on R1 day -1. Asymmetric bet; only attractive if we believe R2 is
much more representative of live than R1.

### 3. Adaptive size based on recent realized VWAP spread

**Mechanism:** Track rolling per-product realized spread over a sliding
window of recent round-trips (e.g., last 50 fills). If the rolling spread
is negative, scale passive quote size toward zero. If positive, allow full
size. Idea: stop doubling down on negative-edge regimes.

**Why plausible:** This is agnostic to the underlying cause. It directly
detects "we are losing money per unit" and reduces exposure.

**Risk:** Noisy signal on small fill counts; could underfire in regime
flips and lose the edge on the transition.

**Rough direction:** Could recover a meaningful fraction of R2 losses
without hurting R1 (since R1 rolling-spread is persistently positive, no
size reduction triggers). Architecturally most complex of the three.

### 4. Fix EMA per-day reset in merged backtest mode

**Mechanism:** Sprint 3 diagnostic surfaced that the production strategy
only resets the EMA on `state.timestamp == 0`, which in merged-backtest
mode fires once at the very start (timestamp 0 of day -1). In live, each
day is a fresh submission with `state.timestamp = 0` at day start. So the
backtest benefits from EMA carry-over that won't exist live, potentially
inflating reported PnL on the non-first days.

**Why plausible:** This is a correctness fix with no tuning component —
aligns backtest to live behavior.

**Risk:** Might make practice PnL look worse (likely by 2–5k on day 0 and
day 1 of each round), but the fix is pure correctness, not tuning. Do this
regardless of the other interventions.

**Rough direction:** Expect backtest numbers to change slightly on days
≥1. Sprint 4 should include this even if no other intervention is chosen.

---

## Confidence and next steps

**Confidence in the primary cause (adverse selection per H5): HIGH.**

- The VWAP-spread flip (+53 → −11, −12) is a direct quantitative measurement,
  not a vibes interpretation. It is the definition of realized edge.
- The falsification of H1, H2, H6 is clean: price dynamics and EMA behavior
  are statistically near-identical across R1 and R2.
- The data shows no other plausible mechanism with comparable magnitude.

**Confidence in specific interventions: LOW.**

- None of the four intervention ideas has been backtested in Sprint 3 (out
  of scope — pure diagnosis).
- There is a real chance that widening `min_edge` or suppressing the drift
  bias hurts R1 more than it helps R2, making round-trip PnL across both
  rounds *worse* on average.
- If R2 live turns out to behave like R1 (positive-edge regime returns),
  any intervention we ship will give back +20–40k of Sprint-2 headroom.

**Is the loss fixable?** A clean answer requires Sprint 4 to backtest
interventions 1, 2, and 3 on **both R1 and R2** and measure the round-trip.
Sprint 3's analysis rules out "just change the EMA threshold" as a
fix — the EMA is not the problem. Any fix will trade some R1 edge for some
R2 safety, and the right bet depends on our prior over live regime.

**Recommended Sprint 4 scope:**

1. Apply Intervention 4 (per-day EMA reset fix) unconditionally — pure
   correctness.
2. Try Intervention 1 (min_edge 2→3 and 2→4) as two separate
   parameter sweeps; measure R1 and R2 totals.
3. Try Intervention 2 (drop `PEPPER_DRIFT_BIAS_SIZE` to 0 or 4) as a
   separate sweep.
4. Avoid Intervention 3 (adaptive sizing) this sprint — it introduces new
   code surface area and the other two may already be enough.
5. Pick the configuration that maximizes `min(R1_total, R2_total)` — a
   robust choice that does not bet on live regime.

No interventions are being applied in Sprint 3.
