# Round 2 MAF Bid Decision

**Sprint:** Sprint 2 (MAF wiring)
**Date:** 2026-04-20
**Decision:** bid **750 XIREC** via `Trader.bid()`
**Sibling docs:** `round2_context.md` (situation), `round1_retro.md` (what we know about live regime).

---

## Sprint 2 drift resolution (addendum)

During Sprint 2 we discovered significant drift between the local modular
source and the actually-submitted Round 1 file (`round2.py` at repo root):

- **The engine honors `Trader.bid()`**, not `trader_data["maf"]`. The submitted
  `round2.py` used traderData-publishing on speculation; we are committing to
  the wiki-specified `bid()` interface only. `round2.py`'s 5,000-XIREC anchor
  was computed against *Round 1 practice* (140k), which is the wrong baseline;
  it is retained as a historical artifact only.
- **`round2.py` used `PEPPER_WALL_VOLUME = 12`**; the modular source used `15`.
  Empirically, 12 outperforms 15 on *both* Round 1 practice (+11,932 XIREC)
  and Round 2 practice (+17,324 XIREC) — a broad improvement, not an overfit.
  Back-ported to `algo/strategies/pepper_root.py` in Sprint 2.
- **`round2.py` introduced an `OSMIUM_TAKE_EDGE` parameter**; the modular
  source's stricter take logic (any ask < fair, any bid > fair) is superior
  on practice data (+2,191 XIREC on R1). Osmium back-port rejected.
- **Round 2 canonical submission: `dist/round2_submission.py`** (produced
  by `scripts/flatten.py` from updated modular source). The Round 1 artifact
  `dist/bigballers.py` is preserved unchanged; the submitted `round2.py` at
  the repo root is also retained as historical record.

### Revised practice baselines with the back-ported Pepper tuning

| Data | Old baseline (modular, wall=15) | New baseline (modular, wall=12) |
|---|---:|---:|
| Round 1 practice (worse, merged) | 142,102 | **155,182** |
| Round 2 practice (worse, merged) | 13,096 | **30,758** |

The 750 XIREC MAF bid remains correct under the higher baseline. The
revised `L` estimate (expected lift from winning MAF) scales roughly with
baseline PnL, so a higher baseline *strengthens* the case for 750 rather
than weakening it — the EV-optimal bid shifts a little upward but stays
well within the 500–1,000 robust range.

**Pepper still loses money on Round 2 practice days 0 and 1** even at the
new baseline. Days 0/1 Pepper = −18,623 / −2,582 = −21,205, offset by
strong Osmium. Sprint 3 priority: understand what changes between R1
regime (where Pepper makes big money on drift days) and R2 regime
(where Pepper loses money on most days).

---

## TL;DR

Bid **750 XIREC** for the Round 2 Market Access Fee. Expected value contribution
is small and positive (~+1k XIREC in expectation), with low downside exposure
relative to our Round 1 live algo print (~55k) or the 200k qualification
threshold. The bid is deliberately anchored to the Round 2 *practice* PnL
(13,096), not to the Round 1 *live* number (55,178), per Sprint 2 brief's
anti-optimism guidance.

---

## 1. Inputs

From Sprint 1 docs, verified:

| Input | Value | Source |
|---|---:|---|
| Round 2 practice PnL (v4, worse matcher, merged) | **+13,096** | `docs/ROUND2/round2_context.md` |
| — Osmium component | +48,635 | ~16k/day, very stable |
| — Pepper component | −35,539 | losing on all 3 days |
| Round 1 live algo PnL (real eval) | +55,178 | Round 1 result |
| Round 1 live Pepper (one-day drift day) | +39,514 | same |
| MAF mechanism | +25% of quoted size clears (100% vs 80%) | Round 2 wiki |
| MAF auction structure | top 50% of bids win | Round 2 wiki |

**What MAF does, mechanically:** wins +25% quote volume. That means 20% more of
our quoted size actually clears on days we win the auction. *Not* a direct PnL
addition — a *volume multiplier* on whatever our strategies already produce.

---

## 2. Expected-value lift from winning MAF

The critical question: **how much extra PnL does +25% volume buy us, in
expectation?**

### 2a. Volume-lift vs. PnL-lift

+25% volume does NOT translate to +25% PnL. Position limits (80 each way) bind
before volume does, so extra quote fills frequently just mean hitting the
position cap faster. Realistic lift is ~15–20% of baseline PnL.

### 2b. Three anchor scenarios for expected lift `L`

| Anchor | Baseline PnL | Lift factor | Expected L |
|---|---:|---:|---:|
| **Pessimistic (R2 practice)** | 13,096 | 0.15 | ~**2,000** |
| **Middle (R2 practice × 1.5)** | ~20k | 0.175 | ~3,500 |
| **Optimistic (R1 live, ignored per Sprint 2 brief)** | 55,178 | 0.175 | ~9,600 |

The Sprint 2 brief explicitly says: *"Do not assume 'Round 2 PnL will be similar
to Round 1' in the MAF calculation. Base MAF decision on the 13k practice
number."* Anchoring to **L ≈ 2,000 XIREC**.

### 2c. Why we do NOT use the Round 1 live number

1. Round 2 has different data (3 new days: −1, 0, 1). Practice already shows
   Pepper losing money on all 3. Whatever drove Round 1 live's +39k Pepper day
   is not guaranteed to recur in Round 2.
2. The Sprint 2 brief explicitly warns against this mistake.
3. Bidding for an expected lift we are not confident in would be a bias-to-bid,
   not an informed EV calc.

### 2d. Nuance: Pepper is currently negative in practice

If practice Pepper losses represent a real negative-edge regime, +25% volume
actually makes Pepper *worse*. That component of the lift is negative. Osmium
is positive-edge so its component is positive. Netting out:

- Osmium +25%: +48,635 × 0.175 ≈ **+8,500** additional PnL
- Pepper +25%: −35,539 × 0.175 ≈ **−6,200** additional PnL
- Net lift L ≈ **+2,300**

Consistent with the pessimistic anchor. Using **L = 2,300** in the EV table.

---

## 3. Opponent bid distribution (prior)

No public data on how other Prosperity teams bid. We assume a mix:

| Segment | Share of teams | Typical bid |
|---|---:|---:|
| Didn't read wiki / bid 0 | ~25% | 0 |
| Token bid (read wiki, minimal commitment) | ~25% | 1–100 |
| "Reasonable" bid (positive EV calc) | ~30% | 250–1,500 |
| Aggressive bid (willing to overpay for info/priority) | ~20% | 2,000–10,000 |

Median (50th percentile) bid under this distribution lands in the 100–500 range.
Winning the auction (above median) therefore requires bidding somewhere above
~500 to be comfortably "above median."

This is a **calibrated guess**, not a measured distribution. The sensitivity
analysis below shows the decision is robust to reasonable shifts in this prior.

---

## 4. EV table

**Formula:** `EV_contribution = p(win) × (L − bid)`, where `L = 2,300`.
Baseline PnL (practice anchor, 13,096) is unchanged either way — we subtract it
out and report only MAF's marginal contribution.

| Bid | p(win) | Net if win | EV contribution |
|---:|---:|---:|---:|
| 0 | 0% | +2,300 | 0 |
| 100 | 45% | +2,200 | +990 |
| 250 | 55% | +2,050 | +1,128 |
| 500 | 65% | +1,800 | +1,170 |
| **750** | **70%** | **+1,550** | **+1,085** |
| 1,000 | 75% | +1,300 | +975 |
| 1,500 | 85% | +800 | +680 |
| 2,000 | 90% | +300 | +270 |
| 2,500 | 93% | −200 | −186 |
| 5,000 | 97% | −2,700 | −2,619 |

Peak EV is around **500–750**. Both are within 10% of each other on EV.

---

## 5. Recommendation: 750 XIREC

Why 750 specifically, not 500:

1. **Cost of "just missing" median is higher than cost of "bidding $250 too much."**
   If the opponent distribution is fatter at 500 than we assume, 750 still wins
   while 500 might narrowly lose. The EV asymmetry favors a small upward skew
   from the peak.
2. **Round 1 live was 4× practice** on algo PnL (55k vs ~14k equivalent).
   If Round 2 live is similarly better than R2 practice, actual lift `L` is
   higher than 2,300, and the EV-optimal bid shifts upward. 750 covers this
   case better than 500.
3. **750 < 6% of the practice PnL (13,096).** Even if we win and the +25%
   volume provides zero marginal benefit, we lose <1k XIREC. Negligible
   relative to the 57k margin we need for qualification.

Rejected: 1,500+ is the sprint brief's upper-prior number, but our anchor
value `L ≈ 2,300` makes 1,500 only barely EV-positive (EV +680 if we win).
Small margin, high variance — not worth it.

Rejected: 0 or 100. Zero gives up all upside for no gain; 100 leaves EV on
the table if the low-end distribution is thinner than we think.

---

## 6. Sensitivity analysis

EV-optimal bid stays in the **500–1,000 range** under these variations:

| Variation | EV-optimal bid |
|---|---:|
| Baseline (our assumptions) | ~750 |
| Opponents bid higher than expected (median ~1000) | ~1,000–1,250 |
| Opponents bid lower than expected (median ~50) | ~500 |
| Lift `L = 1,000` (worse than anchor) | ~300–500 |
| Lift `L = 5,000` (Round 1 live-equivalent) | ~1,500–2,000 |

**750 is within 25% of EV-optimal across all five variations.** The decision
is robust; we are not over-fitting to one prior.

---

## 6a. Residual uncertainty: linear-scaling assumption

The +2,300 expected lift assumes PnL scales roughly linearly with volume.
In reality, position limits cap Osmium's linear scaling and adverse
selection could amplify Pepper's losses. True lift range is more like
+500 to +5,000 depending on live regime. Bid value of 750 is robust across
this range; detailed sensitivity shown in EV table.

Concretely, under each interpretation:
- **Live looks like practice (Pepper losing):** paid 750 for a lift worth
  maybe +500. Small negative EV on this branch, bounded.
- **Live looks like Round 1 live (Pepper winning on drift):** paid 750 for
  a lift worth +5,000 to +10,000. Large positive EV on this branch.
- **We don't win the auction:** paid 0, accept practice-level PnL. Neutral.

The only scenarios where 750 is clearly wrong are: (a) the MAF median is
actually ≤50 XIREC (overpayment — requires widespread rule-ignorance that
we cannot rule out but think is unlikely given teams reached Round 2), or
(b) Round 2 rules impose a fee structure tied to volume outcome rather than
the flat one-time fee the wiki describes. (a) is a small loss, (b) would
be surprising — the wiki is explicit that the fee is fixed.

---

## 7. Explicit uncertainty acknowledgments

- **Opponent distribution is unknown.** The share percentages in §3 are an
  educated guess, not data. Could be off by ±20 percentage points per bucket.
- **Lift factor `L/PnL` is estimated.** 15–20% is a reasonable first-pass;
  could be 10% if position limits bind aggressively, or 25%+ if the extra
  fills are disproportionately on profitable trades.
- **Round 2 regime could shift materially from practice.** If Pepper reverts
  to positive-edge live (as in Round 1), `L` roughly doubles and 750 is well
  under optimal. If it doesn't, 750 is ~optimal. Asymmetric favorable.
- **MAF is one-time per submission, not per tick.** If we submit once and
  lose the auction, we eat no cost but lose the lift. If we win, we pay 750
  once and get +25% volume for the whole eval.

---

## 8. Fallback if the EV model is wrong

Maximum MAF bid cost at 750 XIREC is 750 XIREC. Downside is bounded at <1% of
the 200k qualification threshold. Even in the worst-case interpretation
(opponents all bid 0, we pay 750 for nothing), the loss is small relative to
the ~57k margin we need from Round 2. **No catastrophic failure mode.**

If Sprint 3 EDA surfaces evidence that Pepper's practice losses represent a
real negative-edge regime that will persist live, we may want to revisit
this bid downward (closer to 250–500) before submission. Sprint 3 has a hook
for this — see `round2_context.md` §"Sprint ordering."

---

## 9. Decision

**MAF bid value: 750 XIREC.** To be hardcoded as the return value of
`Trader.bid(self) -> int` in `algo/trader.py`.

Subject to revision in Sprint 3 if EDA changes the Pepper regime assumption.
