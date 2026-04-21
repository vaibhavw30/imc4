# Round 2 Sprint Plan — IMC Prosperity 4

**Status:** Round 1 finished with ~55k XIREC algo PnL + manual challenge answer (~88k if you submitted 30/9999 Flax + 17/19999 Ember). Your total heading into Round 2 should be ~140-150k.
**Goal this round:** Hit 200k qualification threshold (need ~50-60k more). Submit a working MAF bid. Win the manual allocation challenge (worth up to ~300k if played right — this is the single highest-leverage thing this round).
**Current code state:** Round 1 flat submission (`dist/bigballers.py`) has broken MAF stub writing to traderData (it's being ignored by the engine). Strategy logic is unchanged and validated.
**Companion docs:** `docs/PRD.md`, `docs/ROUND_1_INSIGHTS.md`, `docs/round1_retro.md` (TODO).
**Philosophy:** Manual challenge is 60x the expected algo PnL this round. Prioritize accordingly.

---

## Strategic framing

### What Round 2 actually is

Reading the wiki carefully:

1. **Products unchanged.** Same Osmium, same Pepper Root, same 80 position limits. Your existing strategy remains fundamentally sound.

2. **MAF is a blind auction.** You submit a bid via a `bid()` method on your `Trader` class. Top 50% of bidders pay their bid and get +25% quote volume access. Bottom 50% pay nothing and get standard volume. Not a tradeoff-heavy decision — bid in the "comfortably above median" zone at minimum cost.

3. **Testing uses 80% quote volume regardless.** Your 3.6k Round 2 test submission is a LOWER BOUND on real performance. Real eval will be higher by +25% if you win MAF, or unchanged if you don't.

4. **Manual challenge (Research × Scale × Speed) is worth ~200-300k XIREC.** This is the largest single PnL source in the competition so far. Not a throwaway.

5. **Qualification threshold: 200k total.** You're at ~140-150k coming in. You need 50-60k this round. Manual alone will likely deliver this.

### Where PnL comes from this round (expected)

| Source                        | Range        | Notes                                                 |
| ----------------------------- | ------------ | ----------------------------------------------------- |
| Algo (Osmium + Pepper)        | 5-20k        | Test showed 3.6k without MAF bonus; real eval +0-25%  |
| MAF decision                  | -1.5k to 0   | You pay if you win, but win ≈ +2-3k from extra volume |
| Manual (Research/Scale/Speed) | 150-300k     | Dominated by whether you rank well on speed           |
| **Total**                     | **150-320k** | Almost entirely about manual                          |

### What NOT to do this round

- **Don't over-tune the algo.** The 3.6k test number is artificially low due to 80% quote flow + randomization. You can't reliably tune against test noise. Submit a fixed-MAF version and trust the strategy.
- **Don't skip the manual.** It's the biggest PnL opportunity of the round.
- **Don't over-bid MAF.** This is a median auction. Bidding 10k when median is ~500 is lighting money on fire.
- **Don't add new strategy logic.** You have a validated Round 1 strategy. Stick with it.

---

## Sprint overview

| #   | Sprint                                    | Time   | Priority              |
| --- | ----------------------------------------- | ------ | --------------------- |
| 1   | Round 1 retrospective + Round 2 EDA setup | 30 min | Required              |
| 2   | Fix MAF submission mechanism              | 20 min | **Critical**          |
| 3   | Data capsule EDA (check for changes)      | 45 min | Required              |
| 4   | Manual challenge optimization             | 30 min | **Critical**          |
| 5   | Optional: one-parameter algo tune         | 60 min | Skip if short on time |
| 6   | Final submission (algo + manual)          | 30 min | Required              |
| 7   | Post-submission retrospective             | 15 min | Required              |

**Total: ~3.5 hours** minimum, ~4.5 hours with optional algo tune.

---

## Sprint 1 — Round 1 retro + Round 2 data setup

**Goal:** Capture Round 1 learnings. Set up Round 2 data and repo structure.

**Time:** 30 min

### Tasks

1. **Write `docs/round1_retro.md`** with the following sections:
   - Final submitted: v4 (directional EMA overlay)
   - Pre-deadline test PnL: 5,321 (v1/v4 equivalent on drift-free day)
   - Real eval PnL: 55,178 (Osmium 15,664 + Pepper 39,514) on a day with +1001 Pepper drift
   - Manual challenge submitted: Flax (Buy, price=30, vol=9999) + Ember (Buy, price=17, vol=19999) expected ~88k
   - Key insight: EMA threshold=8 was correctly calibrated — triggered on +1001 drift day, dormant on +101 days
   - What would you do differently: probably nothing major — the caution was appropriate given limited data
   - Reusable infrastructure for Round 2+: modular Strategy classes, flatten script, EDA pipeline, diagnostic methodology
2. **Download the Round 2 data capsule** if not already in your repo. Place in `data/round_2/`. File structure likely matches Round 1: `prices_round_2_day_X.csv` format.

3. **Extract and verify data files:**

   ```bash
   ls data/round_2/
   # Expect: prices_round_2_day_{-2,-1,0}.csv (or similar)
   ```

4. **Check the ARIA Uplink page** in the Prosperity platform — there may be Round 2-specific hints about product behavior changes (historically these matter).

5. **Git commit:** `"Round 2 setup — data capsule + retro"`

### Exit criteria

- `docs/round1_retro.md` exists with all sections filled.
- Round 2 data files are in `data/round_2/`.
- Repo is committed with clean state.

---

## Sprint 2 — Fix MAF submission mechanism (CRITICAL)

**Goal:** Your submitted code uses the correct `bid()` method. No more traderData-based guesswork.

**Time:** 20 min

### Background

Your current `dist/bigballers.py` (and `algo/trader.py`) has:

```python
# WRONG — engine ignores this
MARKET_ACCESS_FEE: int = 5000
...
trader_data = json.dumps({"maf": MARKET_ACCESS_FEE})
```

Per the wiki, the correct mechanism is a `bid()` method on the Trader class:

```python
# CORRECT
class Trader:
    def bid(self) -> int:
        return 1500

    def run(self, state: TradingState):
        ...
```

Without the `bid()` method, you're bidding **$0** — guaranteed to lose the auction and get no extra volume.

### Tasks

1. **Determine your MAF bid amount.** Use this logic:
   - Your algo baseline (no MAF, no quote reduction): ~5-10k expected on real eval
   - MAF benefit (+25% quote volume): ~25% more fills → +1-2.5k PnL
   - You bid to land above median; overpaying wastes XIREC
   - Recommended bid: **1,000-2,000 XIREC**
   - I recommend **1,500** as a compromise between "comfortably above likely median" and "not paying much more than the benefit"
   - DO NOT bid above 3,000 unless you have specific reason to believe the median is high
2. **Modify `algo/trader.py`** to add the `bid()` method:

   ```python
   class Trader:
       def __init__(self) -> None:
           self.strategies = {
               "ASH_COATED_OSMIUM": OsmiumStrategy(),
               "INTARIAN_PEPPER_ROOT": PepperRootStrategy(),
           }

       def bid(self) -> int:
           # Round 2 MAF. See docs/round2_maf_reasoning.md for the calculation.
           # Top 50% of bids win; we're in the "comfortably-above-median" zone.
           return 1500

       def run(self, state):
           # ... existing code, but remove the MAF from trader_data ...
           trader_data = ""
           logger.flush(state, result, conversions, trader_data)
           return result, conversions, trader_data
   ```

3. **Delete the old MAF publishing:**
   - Remove `MARKET_ACCESS_FEE: int = 5000` constant
   - Remove `trader_data = json.dumps({"maf": MARKET_ACCESS_FEE})`
   - Clean up the MAF docstring comment

4. **Re-run the flattener:**

   ```bash
   python scripts/flatten.py
   ```

5. **Verify the flat file:**

   ```bash
   head -30 dist/bigballers.py | grep -c "from algo"   # must be 0
   grep "def bid" dist/bigballers.py                    # must find the bid() method
   grep "MARKET_ACCESS_FEE" dist/bigballers.py          # should NOT find the old constant
   python -c "import ast; ast.parse(open('dist/bigballers.py').read())"
   ```

6. **Write `docs/round2_maf_reasoning.md`** documenting the decision — one paragraph is fine. This is for your future self.

7. **Git commit:** `"Fix MAF submission via bid() method, remove traderData guess"`

### Exit criteria

- `bid()` method exists on the Trader class in both `algo/trader.py` and `dist/bigballers.py`.
- `MARKET_ACCESS_FEE` constant is deleted from both files.
- Flat file parses, has zero `from algo.` imports, and contains the `bid()` method.
- Decision documented.

### Risks

- **Forget to re-flatten.** If you update `algo/trader.py` but don't re-run `scripts/flatten.py`, your submission file is stale. Always flatten as the last step.
- **Typo in bid amount.** `return 1500` vs `return 15000` is a 10x overpayment. Eyeball this carefully.

---

## Sprint 3 — Round 2 data capsule EDA

**Goal:** Confirm Osmium and Pepper Root haven't changed in character. Check for anything that would require strategy changes.

**Time:** 45 min

### What we're looking for

The wiki says the products are "the same" but the market has become "more competitive and dynamic." Test whether:

- Osmium fair value is still 10,001
- Pepper's anchor pattern still follows +1000/day or similar structure
- Bid-ask spreads haven't dramatically changed
- Top-of-book depth distributions haven't shifted (affects `wall_mid`)

### Tasks

1. **Extend `analysis/explore.py`** (or write `analysis/explore_round2.py`) to run the same EDA on Round 2 data:
   - Mid-price distribution per product per day
   - Modal values (Osmium should still mode at 10,001)
   - Per-day means for Pepper (check if +1000/day pattern continues or new values)
   - Bid-ask spread distribution
   - Top-of-book depth distribution (informs wall_mid threshold)
   - Return autocorrelation (should still be ~-0.5 on both products)

2. **Run it:**

   ```bash
   python -m analysis.explore_round2
   ```

3. **Compare to Round 1 findings in `docs/ROUND_1_INSIGHTS.md`.** Flag any deltas:
   - If Osmium fair has moved: update `OSMIUM_FAIR_VALUE` constant
   - If Pepper anchors are different: note for awareness (strategy uses wall_mid so it adapts)
   - If spreads have tightened: may want to reduce `OSMIUM_MAKE_EDGE` from 2 to 1
   - If depth distribution shifted: may want to re-tune `PEPPER_WALL_VOLUME`
4. **Write findings to `docs/ROUND_2_INSIGHTS.md`** following the same format as Round 1.

5. **Run a backtest on Round 2 data:**

   ```bash
   prosperity4btest algo/trader.py 2 --data data --merge-pnl --out logs/r2_v1.log
   prosperity4btest algo/trader.py 2 --data data --merge-pnl --match-trades worse --out logs/r2_v1_worse.log
   ```

   Record per-product per-day PnL. Compare to Round 1 backtest results (101k all-match, 117k worse-match on practice data).

6. **Git commit:** `"Round 2 EDA complete, insights documented"`

### Exit criteria

- `docs/ROUND_2_INSIGHTS.md` exists, comparing Round 2 data to Round 1 findings.
- Round 2 backtest completes without errors; PnL recorded.
- Any material parameter changes are flagged (don't apply yet — wait for Sprint 5 if you tune).

### Risks

- **Data format changed between rounds.** If the CSV parser fails, check column names first.
- **Over-interpreting small sample (3 days of data).** Only treat differences as signal if they're large (20%+) or structurally meaningful.

---

## Sprint 4 — Manual challenge (CRITICAL)

**Goal:** Submit the optimal Research/Scale/Speed allocation. This is the single highest-PnL decision of Round 2.

**Time:** 30 min

### The math (summary)

- **Research (R):** logarithmic, maxes at 200,000 for 100% investment
- **Scale (Sc):** linear, maxes at 7 for 100% investment
- **Speed (Sp):** rank-based multiplier from 0.1 (bottom) to 0.9 (top)
- **PnL = R × Sc × Sp − 50,000 × (total_allocation/100)**
- **Total can be 0-100%. You CANNOT exceed 100%.**

### The insight

Because PnL is multiplicative, **zero in any pillar = zero PnL**. So you must allocate something to each. The question is how much.

**Scale is linear and cheap to max.** Each 1% gives you 0.07 Scale. Scale doesn't saturate. **You want Scale high.**

**Research has diminishing returns (log).** R=24 gives you ~139k of Research. R=50 gives you ~170k. R=100 gives you 200k. Marginal return drops fast past 25%.

**Speed is rank-dependent.** Whatever you invest, your PnL multiplier depends on where your Sp% ranks among all participants. If most teams invest ~20%, investing 25% gets you near median (0.5x). Investing 45% gets you top-quartile (0.7x).

### Analysis: best allocation depends on what others do

My Python analysis shows:

**If median Sp allocation across teams is ~20%** (my best guess given bimodal distributions typical in these games):

| Your allocation    | Expected speed mult      | Expected PnL    |
| ------------------ | ------------------------ | --------------- |
| R=23, Sc=76, Sp=1  | ~0.1-0.3 (bottom)        | **24k - 170k**  |
| R=22, Sc=68, Sp=10 | ~0.3-0.4                 | **75k - 290k**  |
| R=20, Sc=55, Sp=25 | ~0.45-0.55 (near median) | **125k - 290k** |
| R=18, Sc=47, Sp=35 | ~0.65-0.75 (upper)       | **180k - 300k** |

**The "very safe" 1% Speed allocation is actually risky.** It assumes you'll get a decent speed rank by default. In practice, lots of teams will invest in Speed chasing the 9x multiplier, so 1% puts you in the bottom bucket.

### Recommendation (with reasoning)

**R=20%, Sc=55%, Sp=25%.**

Why:

- Scale at 55% captures most of its linear value (3.85 out of max 7)
- Research at 20% gives 136k (most of the log curve's value)
- Speed at 25% is competitive — likely median-to-above-median rank
- Total = 100%, so you use the full budget
- Expected PnL: **~230k** with moderate variance (125k-290k range across scenarios)

### Alternative: Aggressive Speed play

If you think most teams will NOT prioritize Speed (they'll go R-heavy because 200k cap looks appealing), then:

**R=18%, Sc=47%, Sp=35%** — higher expected value (~244k expected) but worse downside (~118k worst case).

### Alternative: Safe Scale-heavy play

**R=20%, Sc=60%, Sp=20%** — slightly lower expected PnL but less dependence on speed rank.

### Final call

**Submit R=20, Sc=55, Sp=25.** It's the best balance of expected value and robustness to different opponent distributions.

### Tasks

1. **Read the manual challenge page one more time** to confirm:
   - You can re-submit until round end
   - Total cannot exceed 100%
   - Budget used is subtracted from PnL

2. **Submit via the Prosperity platform UI:**
   - Research: 20%
   - Scale: 55%
   - Speed: 25%

3. **Screenshot the submission confirmation.**

4. **Document in `docs/round2_manual_decision.md`:** one paragraph on the reasoning. You can iterate if time allows.

5. **Git commit:** `"Manual challenge decision: R=20/Sc=55/Sp=25"`

### Exit criteria

- Manual allocation submitted on the platform.
- Confirmation visible (platform shows your submission).
- Decision documented.

### Optional: simulate before submitting

If you have 10 extra minutes, run the Python analysis yourself with different opponent distributions to build intuition. The code I used is in the chat — adapt it as a standalone script in `analysis/manual_optim.py`.

---

## Sprint 5 — Optional: one-parameter algo tune

**Goal:** If you have time, try lowering Pepper's EMA threshold to capture more drift days.

**Time:** 60 min

**Priority:** SKIP if total time remaining is under 2 hours. Sprint 6 must complete before deadline.

### The hypothesis

Your Round 1 real-eval day had +1001 Pepper drift. The pre-deadline test day had only +101 drift. Your current threshold (8.0) triggered on +1001 (rightfully so) but was dormant on +101.

If Round 2's real eval day has moderate drift (say +300-500), threshold 8 might miss it. Lowering to 5 or 6 could help.

### The risk

Lowering the threshold means triggering on more days, including flat/noisy days where you'd churn inventory for no directional gain. You could hurt performance on days where there's no real drift.

### Tasks

1. **Run backtests with threshold variants:**

   ```bash
   # Modify PEPPER_DRIFT_THRESHOLD in pepper_root.py, run each:
   # threshold = 4, 5, 6, 7, 8 (current), 10
   prosperity4btest algo/trader.py 2 --data data --merge-pnl --match-trades worse --out logs/r2_thr_N.log
   ```

2. **For each threshold, record:**
   - Pepper PnL per day
   - Total Pepper PnL (worse matcher)
   - Mean |position| per day (higher = more directional bias firing)
   - Bias flips per day (too many = whipsawing)

3. **Decision rule:**
   - If lowering threshold improves Pepper PnL on worse-matcher by 20%+ across all 3 days, adopt the new value
   - If it improves one day but hurts another, revert — the variance isn't worth it
   - If no clear winner, keep threshold=8

4. **Also check:** what does R2 day data look like in terms of drift magnitude? If daily drift is consistently small (<100 ticks), lower threshold helps. If it's variable, keep threshold=8.

5. **Git commit either way:** `"Pepper threshold tuning — kept X after evaluation"`

### Exit criteria

- Decision made (keep or change) with quantitative backing.
- If changed: re-flatten `dist/bigballers.py`.

### Fallback

If tuning produces ambiguous results after 45 min, don't change anything. Keep threshold=8. The strategy validated on Round 1 real eval is the strategy.

---

## Sprint 6 — Final submission

**Goal:** Submit the final trader code AND confirm manual allocation is set.

**Time:** 30 min

### Tasks

1. **Verify `dist/bigballers.py` is current:**

   ```bash
   ls -la dist/bigballers.py
   # Check timestamp is recent (post Sprint 2 edits)
   ```

   If stale, re-run `python scripts/flatten.py`.

2. **Final sanity checks on `dist/bigballers.py`:**

   ```bash
   head -30 dist/bigballers.py           # Imports clean
   grep "def bid" dist/bigballers.py     # bid() method present
   grep "return 1500" dist/bigballers.py # (or whatever you chose)
   grep "MARKET_ACCESS_FEE" dist/bigballers.py  # Should find nothing
   python -c "import ast; ast.parse(open('dist/bigballers.py').read())"
   ```

3. **Upload to IMC.** Both the algo file and the manual form should be submitted.

4. **Confirm receipts:**
   - Algo: platform should show "last uploaded" timestamp
   - Manual: submission should persist in the form after refresh

5. **Run platform in-app backtest** one more time to sanity check. Expected: non-zero PnL, no errors.

6. **Stop editing.** From this point, any change is risk.

### Exit criteria

- Algo uploaded and platform confirms receipt.
- Manual allocation set and confirmed.
- Platform in-app backtest shows non-error output.
- Deadline buffer ≥ 30 min remaining.

### Buffer

Target completing this sprint at least 30 minutes before deadline. If last-minute platform issues come up, you have recovery time.

---

## Sprint 7 — Post-submission retro

**Goal:** Capture lessons for Rounds 3-5.

**Time:** 15 min

### Tasks

1. Write `docs/round2_retro.md`:
   - Final submitted MAF bid
   - Manual allocation submitted
   - Expected PnL range for algo
   - What you learned (parameter sensitivity, manual game theory)
   - Open questions for Round 3

2. **Commit everything.** Clean repo state before Round 3.

3. **Close the laptop.** Round 3 starts in 72 hours — you have time.

---

## Decision summary (if you're short on time)

If you can only do 3 things:

1. **Add `def bid(self): return 1500` to Trader class, re-flatten, re-upload.** (Sprint 2) This fixes the broken MAF and is a 20-minute task.
2. **Submit manual: R=20, Sc=55, Sp=25.** (Sprint 4) Biggest PnL source in the round.
3. **Don't tune the algo.** Test PnL is noisy; real eval will be fine.

---

## Risk register

| Risk                                | Mitigation                                                             |
| ----------------------------------- | ---------------------------------------------------------------------- |
| MAF bid typo (extra zero)           | Eyeball before flattening; grep for exact value                        |
| Flatten not run after edits         | Final Sprint 6 checks include verifying flat file is current           |
| Manual allocation submitted wrong   | Screenshot + re-verify after submitting                                |
| Over-tune algo on noisy test data   | Sprint 5 is explicitly optional with clear skip criterion              |
| Speed rank much lower than expected | Sprint 4 recommends Sp=25 specifically to avoid bottom-percentile trap |
| Platform upload fails at deadline   | 30-min buffer built into Sprint 6                                      |

---

## Definition of Done

Round 2 is done when:

- [ ] `dist/bigballers.py` has working `bid()` method and no traderData MAF
- [ ] Platform confirms algo upload
- [ ] Manual allocation submitted (R, Sc, Sp percentages set)
- [ ] Platform in-app backtest produces non-zero output with no errors
- [ ] `docs/round2_retro.md` written
- [ ] Git committed, clean state
- [ ] You close the laptop with ≥30 min before deadline

Expected Round 2 total PnL range: **150k - 320k** (dominated by manual).
Post-Round 2 cumulative: **290k - 470k** (well past the 200k qualification threshold).

You're set up for the harder rounds ahead.
