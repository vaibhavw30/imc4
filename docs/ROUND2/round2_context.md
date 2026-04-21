# Round 2 Strategic Context

**Sprint:** Sprint 1 (Round 1 retro + Round 2 data setup)
**Date:** 2026-04-19
**Scope:** What Round 2 changes, what it doesn't, and where the PnL comes from.
**Sibling doc:** `round1_retro.md` (what we shipped in Round 1 and what we learned).

---

## The situation

- **Cumulative XIREC heading into Round 2 (working estimate):** ~**143k**.
  - Algo (confirmed by IMC): 55,178.
  - Manual (expected, not yet confirmed): ~87,995.
  - **This number depends on the manual PnL landing as expected.** Sanity-check against IMC's official tally before relying on it.
- **Qualification threshold:** **200k XIREC** cumulative.
- **Minimum needed from Round 2:** ~**57k**.
- **Risk buffer we'd like:** we should aim for a meaningful buffer over 57k — not because the Round 2 algo has to carry the round, but because manual-challenge results are variable and a single weak manual can eat our margin in one round.

---

## What Round 2 adds

1. **Market Access Fee (MAF) mechanism.**
   - Submitted via a new `bid(self)` method on the `Trader` class — NOT via `traderData`, NOT via any side channel.
   - MAF is a **one-time fee** paid per bid, not per tick.
   - The top **50% of bids** win access to **+25% quote volume** for that submission (i.e. 100% of your quoted size clears instead of 80%).
   - **Test environment** always runs at 80% (MAF is not awarded in testing).
   - **Real eval:** 100% volume if you win MAF, 80% otherwise.

2. **Manual challenge — 3-pillar allocation.**
   - 50k budget allocated across **Research / Scale / Speed** pillars.
   - Allocation strategy is an opponent-distribution problem, like Round 1's Flax/Ember buy-levels.

3. **No new products.** Same `ASH_COATED_OSMIUM`, same `INTARIAN_PEPPER_ROOT`, same 80 position limits.

---

## What Round 2 does NOT change

- **Products and limits.** Two products, 80 each way. Our strategies are reusable as-is.
- **Backtester / data format.** `data/ROUND_2/` CSVs have the same column headers as Round 1 — confirmed by direct `head` comparison. `analysis/load_data.py` works unchanged.
- **Our strategy files.** `algo/strategies/osmium.py` and `algo/strategies/pepper_root.py` do not need edits for Round 2 on the MAF axis. They may need edits if the Round 2 market regime differs materially from Round 1 (Sprint 3 will analyze).

---

## Expected PnL sources (Round 2)

Rough, pre-analysis priors. Sprint 3 should refine these numbers against
`data/ROUND_2/` EDA.

| Source | Expected PnL range | Rationale |
|---|---:|---|
| **Algo** | **+5k to +15k most likely; wider range live** | Round 2 practice backtest (v4, worse matcher, merged 3 days) prints +13,096 — in the middle of the expected range. Live could surprise either way depending on Pepper drift regime. |
| **Manual** | **+200k to +300k if played correctly** | This is the biggest single PnL source of the round. Opponent-distribution problem, same genre as Round 1. Critical to execute well. |
| **MAF** | **Neutral to slightly positive** | +25% volume on a positive-edge strategy should be positive EV. A reasonable first-pass bid is ~1,500 (roughly one good day's MM edge); treat MAF as an EV-positive option, not a PnL driver. |

**Total Round 2 expectation:** ~**210k–320k** if algo and MAF are neutral-positive and manual is executed well. Comfortably above the ~57k threshold we need to hit 200k cumulative.

---

## Known issues to fix in Round 2 code

1. **`bid()` method does not exist.**
   - Sprint 2 deliverable: add `def bid(self) -> int` to the Trader class in both `algo/trader.py` and (after re-flatten) `dist/bigballers.py`.
   - Return value is the MAF bid in XIREC. Specific value TBD from Round 2 analysis.

2. **Historical note on the Sprint 1 brief.**
   - The Sprint 1 brief predicted that the current v4 code has "broken MAF writing to traderData" that needs to be stripped out. **Verified false.** There is no `MARKET_ACCESS_FEE` constant and no MAF-related traderData publishing anywhere in the tree. The code is clean; Sprint 2 only has to *add* a `bid()` method, not remove anything.

3. **No per-tick position trace from the Round 1 live eval.**
   - Add logging in Round 2 so the next retro can decompose per-product PnL into MM-edge vs inventory-drift components.

---

## Known unknowns

- **Round 2 price regime.** `data/ROUND_2/` has three days (−1, 0, 1). We have not yet EDA'd drift magnitudes or tick std for either product. Sprint 3 will answer. If Pepper drift differs materially from Round 1, the `PEPPER_DRIFT_THRESHOLD=8` calibration may need re-examination.
- **Opponent distribution for MAF bids.** Not observable pre-round. Will need a prior + fallback plan in Sprint 2. One heuristic: set the bid at a fraction of a "median good MM day" so even if we lose we haven't given away a day's PnL.
- **Opponent distribution for the Research / Scale / Speed manual allocation.** Also not observable; same class of problem as the Flax/Ember buy levels in Round 1.
- **Leaderboard semantics.** Is the leaderboard **cumulative** across rounds, or does it **reset** per round? Check the ARIA uplink / Round 2 wiki. Matters for how much risk we should take on the Round 2 algo: cumulative → steady-and-safe; reset → need to clear ~57k within Round 2 alone.
- **Actual Round 1 manual result.** Still unknown to us as of this writing. Cumulative number could shift by ±20k depending on the answer.

---

## Sprint ordering from here

1. **Sprint 2 — MAF wiring.** Add `bid()` method to Trader. Choose an initial bid based on Sprint 1's rough priors (or defer the value to Sprint 3 once we have Round 2 EDA).
2. **Sprint 3 — Round 2 EDA.** Run `analysis/explore.py` against `data/ROUND_2/`. Compare drift, tick std, wall structure vs Round 1. Refine algo-PnL expectation and MAF bid level.
3. **Sprint 4+ — strategy tuning (only if EDA shows the Round 1 calibration doesn't transfer).**
4. **Sprint N — manual allocation across Research / Scale / Speed.** Separate workstream from the algo code path.
