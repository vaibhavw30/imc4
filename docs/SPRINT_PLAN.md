# Sprint Plan

## IMC Prosperity 4 — Round 1 Algorithmic Trading System

**Companion document to:** `docs/PRD.md`
**Plan horizon:** April 16, 2026 → April 17, 2026 (Round 1 deadline at 12:00 CEST / 06:00 ET)
**Total wall-clock time available:** ~14 hours of evening/morning work
**Planning philosophy:** Small sprints, clear exit criteria, explicit "stop and reassess" checkpoints. Strategy work only begins after tooling works.

---

## 0. Pre-Sprint Orientation

### 0.1 Read this first

Three principles govern the order of work:

1. **Tooling before strategy.** Without a working backtester → visualizer pipeline, you cannot validate any strategy hypothesis. Every hour spent on strategy before tooling is at risk of being thrown away.
2. **Data before code.** Before writing strategy logic, confirm from the actual Round 1 CSVs which product is stable and which is drifting. Assumptions are not allowed to survive contact with data.
3. **Ship before polish.** A working mediocre strategy submitted 2 hours early beats a brilliant strategy that misses the deadline. Each sprint has a "good enough to submit" state as its exit criterion.

### 0.2 Sprint structure

Each sprint below includes:

- **Goal** — what's true when this sprint is done
- **Time budget** — hard cap; if exceeded, stop and reassess
- **Tasks** — ordered checklist
- **Exit criteria** — specific, verifiable facts that must hold
- **Deliverables** — files, logs, or data that prove the sprint is complete
- **Risks** — what commonly goes wrong at this step
- **Fallback** — what to do if this sprint runs long

### 0.3 Total sprint map

| #   | Sprint                              | Budget | Wall-clock                        |
| --- | ----------------------------------- | ------ | --------------------------------- |
| 0   | Environment & tooling               | 1.5h   | Night 1, first block              |
| 1   | Data exploration                    | 1.5h   | Night 1, second block             |
| 2   | Scaffolding & empty Trader          | 1h     | Night 1, third block              |
| 3   | Osmium v1                           | 2h     | Night 2, first block              |
| 4   | Osmium tuning & validation          | 1.5h   | Night 2, second block             |
| 5   | Pepper Root v1 (with no-trade band) | 2h     | Morning of deadline, first block  |
| 6   | Pepper Root tuning & validation     | 1.5h   | Morning of deadline, second block |
| 7   | Final integration & submission      | 1.5h   | 2+ hours before deadline          |
| 8   | Post-submission retrospective       | 0.5h   | After deadline                    |

Total: 13h budgeted against 14h available, leaving ~1h of true buffer.

---

## Sprint 0 — Environment & Tooling

**Goal:** A backtester runs an empty Trader end-to-end, produces a log file, and that log file renders in the visualizer. No strategy code written yet.

**Time budget:** 1.5 hours. **If exceeded by 30 minutes, stop and diagnose tooling before proceeding to any other sprint.**

### Tasks

1. **Create and activate virtual environment** from the repo root:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies:**
   ```bash
   pip install prosperity4btest pandas numpy matplotlib
   ```
   Then freeze them into `requirements.txt`:
   ```bash
   pip freeze | grep -E "prosperity4btest|pandas|numpy|matplotlib" > requirements.txt
   ```
3. **Verify the backtester CLI is available:**
   ```bash
   prosperity4btest --help
   ```
   You should see usage output. If not, the venv isn't activated or the install failed.
4. **Grab the sample `Trader`** from `github.com/nabayansaha/imc-prosperity-4-backtester/blob/master/sample.py`. This is a known-good empty-ish Trader with the correct `Logger` class attached. Save it to `algo/trader.py` (create the `algo/` directory).
5. **Run a backtest on Round 0 (tutorial) data** to confirm the pipeline works end-to-end:
   ```bash
   prosperity4btest algo/trader.py 0 --out logs/sanity.log
   ```
   Round 0 is used here because it's what the backtester ships with data for; Round 1 data has to be placed in `data/` separately and pointed to via `--data`. The goal is just to confirm the tool runs.
6. **Run the backtest against Round 1 data** using the `--data` flag to point at your `data/` directory:
   ```bash
   prosperity4btest algo/trader.py 1 --data data --out logs/sanity_round1.log
   ```
   If this fails, inspect the CSV filenames — they must match the backtester's expected pattern (`prices_round_1_day_-2.csv`, etc.).
7. **Open `https://prosperity.equirag.com/`** in a browser and upload `logs/sanity_round1.log`. Confirm you see price charts and order book visualization.

### Exit criteria

- `.venv` exists and is activated.
- `prosperity4btest --help` returns usage.
- `logs/sanity_round1.log` exists and is non-empty.
- The visualizer renders the log without errors and you can see price levels over time for both Round 1 products.

### Deliverables

- `.venv/` (gitignored)
- `requirements.txt`
- `algo/trader.py` (sample version from the backtester repo, unmodified)
- `logs/sanity_round1.log`

### Risks

- **macOS system Python version too old.** Fix: `brew install python@3.11`, recreate venv with that.
- **SSL / certificate errors on pip install.** Fix: `pip install --upgrade certifi` or update macOS system certificates.
- **Visualizer rejects the log format.** Cause: sample.py from the fork might have a modified Logger. Fix: pull the Logger class from jmerle's original P3 repo, overwrite the one in your sample.

### Fallback

If tooling isn't working after 2 hours, switch to IMC's in-platform backtester for this round. You lose local iteration speed but you don't lose the round. Re-attempt local tooling after submission.

---

## Sprint 1 — Data Exploration

**Goal:** You know, from the data, which product is stable and which is drifting, what Osmium's fixed fair value is, and roughly what Pepper Root's bid-ask spread distribution looks like.

**Time budget:** 1.5 hours.

### Tasks

1. **Create `analysis/load_data.py`** with the three functions specified in the PRD:
   - `load_prices(round_num, day)` — reads one CSV with `sep=";"`
   - `load_all_days(round_num)` — loads all three days (-2, -1, 0)
   - `split_by_product(df)` — returns `{product_name: df}`

   Handle the CSV's semicolon delimiter and missing `bid_price_2`/`bid_price_3` columns (they're often empty for the first or last levels).

2. **Create `analysis/explore.py`** as a runnable script. It should:
   - Load all three days for Round 1.
   - For each product (Osmium, Pepper Root), print to stdout:
     - Total timesteps across days
     - Mid-price: mean, std, min, max, median
     - **Mode and modal frequency** (critical for identifying Osmium's fixed value)
     - Percentiles at 1, 5, 25, 50, 75, 95, 99
     - Bid-ask spread: mean, median, 95th percentile
     - Return autocorrelation at lags 1, 5, 10 (pandas: `.pct_change().autocorr(lag=k)`)
     - Rolling 100-tick std of returns: mean and max
   - Save PNGs to `analysis/plots/`:
     - `{product}_price_day_{d}.png` — mid-price time series
     - `{product}_histogram.png` — mid-price histogram
     - `{product}_spread.png` — bid-ask spread distribution
     - `{product}_returns_acf.png` — autocorrelation bar chart for lags 1–20
   - Print a final summary classifying each product:
     - "STABLE — modal frequency >50%, mid-price mode = X" → market-make at fixed fair value X
     - "DRIFTING — mid-price wanders across >10 distinct values" → market-make using wall_mid

3. **Run the script:**
   ```bash
   python -m analysis.explore
   ```
4. **Inspect the plots.** Osmium's histogram should spike at one integer (your `fair_value`). Pepper Root's should be spread across a range.

### Exit criteria

- `analysis/explore.py` runs without error.
- Stdout identifies the Osmium fair value as a specific integer with >50% modal frequency.
- Stdout identifies Pepper Root as drifting with a clear volatility number.
- 8 PNGs exist in `analysis/plots/`.
- You have written down (in comments or a scratch note): Osmium's fair value, Pepper Root's typical spread, and whether return autocorrelation suggests mean-reverting behavior.

### Deliverables

- `analysis/load_data.py`
- `analysis/explore.py`
- `analysis/plots/*.png` (8 files)
- A one-paragraph note on what you learned (written wherever — slack, a scratchpad, a comment at the top of `explore.py`).

### Risks

- **CSV parse errors.** The IMC CSV format has quirks: semicolons, sometimes trailing separators, sometimes NaN in higher-level bid/ask columns. Use `pd.read_csv(path, sep=";", na_values=[""])` and expect NaNs in `bid_price_2`, `bid_price_3`, etc.
- **Column names differ slightly from Prosperity 3.** If something's off, print `df.columns.tolist()` and adjust.
- **Pepper Root has no clear modal value.** That's expected — it's the drifting product. Don't force a fair value onto it.

### Fallback

If plot generation is slow or breaks, skip plots and rely on stdout statistics alone. The modal value of Osmium and the spread distribution of Pepper Root are the critical outputs; visuals are for later debugging.

---

## Sprint 2 — Scaffolding & Empty Trader

**Goal:** Full repo structure is in place. The `Trader` class dispatches to per-product strategies. Each strategy currently returns `[]`. The backtester runs this scaffolding and produces zero PnL (but no errors).

**Time budget:** 1 hour.

### Tasks

1. **Create the full directory structure** as specified in the PRD (Section 5.3). Make sure `__init__.py` files exist in `algo/`, `algo/strategies/`, `algo/utils/`.

2. **Write `algo/utils/order_book.py`** with `best_bid`, `best_ask`, `mid_price`, `wall_mid`. Keep these pure and side-effect-free.

3. **Write `algo/utils/position.py`** with `clamp_order_size` and `inventory_skew`.

4. **Write `algo/strategies/base.py`** with the abstract `Strategy` class.

5. **Write `algo/strategies/osmium.py`** with an `OsmiumStrategy` class that inherits from `Strategy` and currently returns `[]` from `run()`. Accepts `fair_value` and `position_limit` in `__init__`.

6. **Write `algo/strategies/pepper_root.py`** with a `PepperRootStrategy` class that similarly returns `[]` for now. Accepts `position_limit`, `min_edge`, `band_width` in `__init__`.

7. **Rewrite `algo/trader.py`** (overwriting the sample) to:
   - Keep the jmerle `Logger` class verbatim.
   - Instantiate both strategies with placeholder parameters.
   - Dispatch in `run()` with try/except around each strategy.
   - Flush the logger and return.

   At the top of the file, add a comment header documenting that this file may need to be inlined for submission depending on IMC's rules.

8. **Run the backtest:**
   ```bash
   ./run_backtest.sh  # after creating it per PRD
   ```
   Expected result: zero PnL, no errors, log renders in visualizer.

### Exit criteria

- All files in the repo structure exist.
- `prosperity4btest algo/trader.py 1 --data data` runs to completion with exit code 0.
- The resulting log shows both Osmium and Pepper Root in the visualizer with order book data but no fills from our algorithm.

### Deliverables

- The complete file tree as specified in PRD section 5.3, minus any strategy logic (all `run()` methods return `[]`).
- `run_backtest.sh` (executable).
- `.gitignore` covering `.venv/`, `logs/`, `analysis/plots/*.png`, `__pycache__/`.
- `README.md` with setup and run instructions.

### Risks

- **Import errors on package structure.** The backtester imports your `trader.py` as a module. If `trader.py` uses `from algo.strategies.osmium import ...`, the Python path needs to include the repo root. Fix by running `prosperity4btest` from the repo root (not from inside `algo/`).
- **Platform may not support package structure.** See PRD risk 8.6. Flag in README but don't solve yet — we deal with this at submission time.

### Fallback

If the package structure causes import issues, inline all utilities and strategies into a single `algo/trader.py` for now. This is the eventual submission format anyway.

---

## Sprint 3 — Osmium v1

**Goal:** Osmium strategy is implemented with take + make logic and basic inventory skew. Local backtest shows positive PnL on at least 2 of 3 days.

**Time budget:** 2 hours.

### Tasks

1. **Set Osmium's `fair_value`** in `algo/strategies/osmium.py` to the integer identified in Sprint 1 (not the placeholder 10000). Leave a comment: `# calibrated from analysis/explore.py output, <date>`.

2. **Implement the take logic:**
   - Get current position from `state.position.get(self.symbol, 0)`.
   - For each ask price in `order_depth.sell_orders` where `price < fair_value`:
     - Compute the max buy size as `clamp_order_size(position, abs(volume), position_limit)`.
     - Submit a buy order at that price for that size.
     - Update a local position counter so you don't over-submit within this tick.
   - Symmetric logic for bids above `fair_value` (we sell).

3. **Implement the make logic:**
   - Determine passive bid price: `fair_value - 1` (or `fair_value - 2` if you want wider spread).
   - Determine passive ask price: `fair_value + 1` (or `fair_value + 2`).
   - Size each side based on remaining position capacity: how much more can you buy before hitting `-position_limit`? How much can you sell before hitting `+position_limit`?
   - Submit at least one order on each side unless you're already at the limit on that side.

4. **Add inventory skew (light version):**
   - If position > 50% of limit (long): reduce bid size, increase ask size.
   - If position < -50% of limit (short): reduce ask size, increase bid size.
   - Keep this simple — a single branch with adjusted sizes is fine.

5. **Run the backtest on all 3 days:**

   ```bash
   prosperity4btest algo/trader.py 1 --data data --merge-pnl
   ```

6. **Inspect results:**
   - PnL per day per product (backtester prints this).
   - Open the log in the visualizer; scrub through time and verify your orders appear where expected.
   - Look for: did we get filled? Are passive quotes appearing? Are there any cancellations (position breaches)?

### Exit criteria

- Osmium PnL is positive on at least 2 of 3 days.
- No position-limit breaches in the log.
- No Python exceptions.
- In the visualizer, your quotes are visible near the fair value and some of them get filled.

### Deliverables

- `algo/strategies/osmium.py` — complete with take, make, and inventory skew.
- Backtest logs showing positive Osmium PnL.

### Risks

- **Take logic filling too aggressively, not leaving room for passive fills.** Symptom: positive PnL but low total volume. Fix: size take orders more conservatively (e.g., cap at 50% of position capacity).
- **Passive orders never filling.** Symptom: no fills on the make side. Cause: the backtester may only match market-trade flow against your orders if they're at the best price. Tighten passive quotes to `fair_value - 1 / fair_value + 1`.
- **Position drifting and stuck.** Symptom: long position that never comes back. Cause: weak inventory skew. Fix: if |position| > 80% of limit, flatten aggressively by quoting at fair_value on the heavy side.

### Fallback

If Osmium PnL is still negative on 2+ days after 2 hours, strip the inventory skew and go pure take + narrow make. Simpler is better.

---

## Sprint 4 — Osmium Tuning & Validation

**Goal:** Osmium parameters are tuned for stable performance across all 3 days. PnL is positive and consistent.

**Time budget:** 1.5 hours.

### Tasks

1. **Define the parameter grid.** For Osmium, the tunable knobs are:
   - `passive_bid_offset`: {1, 2, 3} (how far below fair value to quote bid)
   - `passive_ask_offset`: {1, 2, 3} (how far above fair value to quote ask)
   - `skew_threshold_pct`: {40, 50, 60} (percentage of limit at which to start skewing)

2. **Write a simple grid-search driver** — a short Python script in `analysis/tune_osmium.py` that:
   - Iterates over all parameter combinations.
   - Modifies the strategy (either by rewriting the file or via a subclass that overrides parameters).
   - Invokes the backtester as a subprocess.
   - Parses the PnL output.
   - Records results in a DataFrame.

3. **Run the grid search** and look at the resulting surface:
   - Which (bid_offset, ask_offset) combos produce positive PnL on all 3 days?
   - Is there a flat plateau of good performance, or a single peak?
   - Pick parameters in the middle of the plateau, not at the peak.

4. **Hardcode the chosen parameters** in `osmium.py`.

5. **Run one more validation backtest** and confirm the PnL matches what the grid search reported.

### Exit criteria

- Grid search results saved to `analysis/tune_osmium_results.csv`.
- Chosen parameters produce positive PnL on all 3 days.
- The chosen parameters are in the middle of a stable region (nearby parameter combos also perform well).
- Osmium's final mean PnL across 3 days meets or exceeds the PRD target (>2,000).

### Deliverables

- `analysis/tune_osmium.py`
- `analysis/tune_osmium_results.csv`
- Updated `algo/strategies/osmium.py` with tuned parameters and a comment citing the tuning run.

### Risks

- **Grid search takes too long.** With 3x3x3 = 27 combinations × 3 days × ~30 seconds per backtest = ~40 minutes. If slower, reduce the grid.
- **No clear plateau.** Symptom: every parameter combo produces wildly different PnL. Cause: the strategy is too sensitive; the edges are not robust. Fix: pick the combo with the lowest PnL variance across days, not the highest mean.

### Fallback

If grid search is unworkable, just pick parameters manually: `bid_offset=1, ask_offset=1, skew_threshold=50`. These are reasonable defaults and likely close to optimal.

---

## Sprint 5 — Pepper Root v1 (with no-trade band)

**Goal:** Pepper Root strategy is implemented using `wall_mid` + no-trade band. Local backtest shows non-negative PnL on at least 2 of 3 days.

**Time budget:** 2 hours.

### Tasks

1. **Implement `wall_mid`-based fair value** in `PepperRootStrategy.run()`:
   - Compute `fair = wall_mid(order_depth, min_volume=15)`.
   - If `fair is None`, fall back to `mid_price(order_depth)`.
   - If that's also None (empty book), return `[]`.

2. **Apply the no-trade band:**
   - Only submit a take order if the edge exceeds `min_edge` (default: 2). That is, only buy asks priced at or below `fair - min_edge`, only sell bids priced at or above `fair + min_edge`.
   - Only submit passive make orders at `fair - band_width` and `fair + band_width`, where `band_width >= min_edge` (default: 3).

3. **Apply the same inventory skew logic** as Osmium — reduce one side when the position gets lopsided.

4. **Start with conservative parameters:** `min_edge=2`, `band_width=3`, `max_order_size=10`. These are small. We expand them if PnL is solidly positive; we tighten if losing.

5. **Run the backtest** on all 3 days.

6. **Compare against a "do nothing" baseline** — temporarily have PepperRootStrategy return `[]`, rerun, and note the PnL (should be 0 for Pepper Root). Our real strategy must beat this zero baseline.

### Exit criteria

- Pepper Root PnL is ≥ 0 on at least 2 of 3 days in the local backtest.
- Combined Round 1 PnL (Osmium + Pepper Root) is greater than Osmium alone in Sprint 4.
- No position breaches.

### Deliverables

- `algo/strategies/pepper_root.py` — complete.
- Backtest log with both products trading.

### Risks

- **Pepper PnL stays negative across all bands.** This is a known risk from Discord. If every parameter combo loses money, we are better off submitting an empty strategy for Pepper. Do not force trades for the sake of trading.
- **Wall mid is noisy or returns None frequently.** Symptom: fair value is erratic tick-to-tick, causing wide quote swings. Fix: apply a short EMA smoothing (e.g., `alpha=0.3`) to stabilize.

### Fallback

If Pepper is solidly losing after 2 hours of tuning, submit empty Pepper (`return []` from `run()`). Zero PnL is strictly better than negative PnL. Document this decision in the submission note and plan to revisit Pepper in Round 2's spare time.

---

## Sprint 6 — Pepper Root Tuning & Validation

**Goal:** Pepper Root parameters are tuned. Final combined Round 1 backtest PnL meets PRD targets.

**Time budget:** 1.5 hours.

### Tasks

1. **Grid search on `min_edge` and `band_width`:**
   - `min_edge` ∈ {1, 2, 3, 4}
   - `band_width` ∈ {2, 3, 4, 5} (with constraint `band_width >= min_edge`)
   - 10 valid combinations × 3 days × ~30s = ~15 minutes.

2. **Optionally add EMA smoothing on wall_mid.** If you tried this in Sprint 5 and it helped, keep it. If it didn't, drop it.

3. **Pick the stable plateau**, not the peak. Same philosophy as Osmium.

4. **Run the final combined backtest:**

   ```bash
   prosperity4btest algo/trader.py 1 --data data --merge-pnl --match-trades worse
   ```

   Note the `--match-trades worse` flag — this is a more conservative matching rule that better approximates the live platform. If PnL drops significantly vs. the default, the edges may be weaker than they appeared.

5. **Compare local backtest PnL to a platform backtest** — upload the current algorithm to IMC's in-platform backtester and compare. They should be roughly in the same ballpark. If they differ by 2x or more, something is off.

### Exit criteria

- Pepper parameters chosen from a stable region of the grid.
- Combined PnL (Osmium + Pepper) ≥ 5,000 XIRECS per day averaged across 3 days.
- PnL variance across days < 30% of mean.
- Local backtest PnL and platform backtest PnL are within 50% of each other.

### Deliverables

- `analysis/tune_pepper_results.csv`
- Final tuned `algo/strategies/pepper_root.py`
- One final combined backtest log for the submission version.

### Risks

- **Local and platform PnL diverge sharply.** Causes: bot behavior differences, simulation edge cases. Trust the platform backtester more — it is closer to the real evaluation environment.
- **Adding Pepper hurts total PnL.** If combined PnL is less than Osmium alone, Pepper is net-negative. Fall back to empty Pepper.

### Fallback

Re-use Sprint 5's fallback: empty Pepper strategy if nothing works. Submit an Osmium-only algorithm.

---

## Sprint 7 — Final Integration & Submission

**Goal:** Algorithm is submitted to IMC with 2+ hours of buffer before the deadline. Receipt confirmed.

**Time budget:** 1.5 hours.

### Tasks

1. **Check IMC's submission form** on `prosperity.imc.com`. Determine:
   - Single file or multi-file upload?
   - Any size or naming constraints?
   - Can you test the upload before final submission?

2. **If single-file is required, inline the package** into a submission file:
   - Create `submission/trader_submission.py`.
   - Manually concatenate (in order): Logger class, utility functions from `order_book.py` and `position.py`, the `Strategy` base class, `OsmiumStrategy`, `PepperRootStrategy`, then the `Trader` class.
   - Remove the now-redundant `from algo...` imports.
   - Verify it's still valid Python (`python -c "import ast; ast.parse(open('submission/trader_submission.py').read())"`).
   - Run one final backtest against this flat file to confirm it behaves identically:
     ```bash
     prosperity4btest submission/trader_submission.py 1 --data data --merge-pnl
     ```

3. **Final verification checklist:**
   - [ ] Position limits match the Round 1 problem statement (not the default 50 unless that's what IMC specified).
   - [ ] Osmium's `fair_value` matches the mode from the data exploration.
   - [ ] No `print()` calls except via the `Logger.print()` method.
   - [ ] No debug code or commented-out strategies.
   - [ ] No external imports beyond stdlib, `datamodel`, and (if used) `numpy`/`pandas`. Note: IMC's sandbox may not allow all pandas operations at runtime, so prefer stdlib for in-algorithm logic.
   - [ ] Final backtest PnL is positive and matches your expectations.

4. **Submit to IMC.** Upload the file via the platform UI.

5. **Verify submission was accepted.** The platform usually shows a "last uploaded" timestamp and may run a quick sanity check. Confirm no errors.

6. **Run one more backtest on the platform's in-app backtester** using the submitted algorithm to confirm it executes in IMC's environment.

7. **Stop making changes.** After submission, do not tweak unless something is objectively broken. Late-deadline changes are the #1 cause of self-inflicted disasters.

### Exit criteria

- Algorithm uploaded to IMC with 2+ hours before the 12:00 CEST / 06:00 ET deadline.
- Platform confirms receipt.
- Platform's in-app backtest of the submitted file produces non-error output.

### Deliverables

- `submission/trader_submission.py` (if inlined).
- Screenshot or note confirming successful upload.

### Risks

- **Last-minute bugs from inlining.** Mitigation: run the final backtest against the inlined file, not just the modular version.
- **Platform upload UI is slow or buggy.** Mitigation: submit with 2+ hours of buffer so you have time to retry.
- **File is rejected for size or syntax.** Mitigation: validate Python syntax locally first; watch the platform's response carefully.

### Fallback

If final integration is failing and time is running out, submit the sample Trader (unmodified, from Sprint 0). It will do nothing but it won't lose money — and you'll at least have a valid submission for Round 1. You can iterate in Round 2.

---

## Sprint 8 — Post-Submission Retrospective

**Goal:** Capture learnings for Rounds 2–5 while they're fresh.

**Time budget:** 30 minutes.

### Tasks

1. **Write a retro note** (`docs/round1_retro.md`) covering:
   - Final submitted PnL (local backtest).
   - Leaderboard rank when results post.
   - What worked.
   - What didn't work.
   - What you'd do differently.
   - Tooling issues encountered.
   - Things to fix in the scaffolding before Round 2.

2. **Note Round 2 prep items** — Prosperity 2 and 3 both had basket/ETF products in Round 2. Start reading about statistical arbitrage and pairs trading in any downtime between Rounds 1 and 2.

3. **Commit everything.** A clean git history of Round 1 is useful reference material for Rounds 2–5.

### Exit criteria

- Retro note written.
- Repo fully committed.
- Mentally ready to switch contexts to Round 2.

### Deliverables

- `docs/round1_retro.md`
- Clean `git status`.

---

## Appendix A — Risk Register

| #   | Risk                              | Sprint | Likelihood | Impact    | Mitigation                                        |
| --- | --------------------------------- | ------ | ---------- | --------- | ------------------------------------------------- |
| 1   | Tooling setup exceeds budget      | 0      | Medium     | High      | Hard stop at 2h; fall back to platform backtester |
| 2   | Data CSV format surprises         | 1      | Low        | Medium    | Inspect with `df.head()` early; adjust loader     |
| 3   | Package import issues on platform | 2, 7   | Medium     | High      | Plan for single-file inline in Sprint 7           |
| 4   | Osmium PnL negative               | 3, 4   | Low        | High      | Pure take strategy as fallback                    |
| 5   | Pepper Root PnL negative          | 5, 6   | High       | Medium    | Empty Pepper strategy as fallback                 |
| 6   | Local/platform PnL divergence     | 6, 7   | Medium     | Medium    | Cross-check before final submission               |
| 7   | Deadline crunch                   | 7      | Low        | Very High | 2h buffer enforced; fallback to sample Trader     |
| 8   | Overfitting to 3 days             | 4, 6   | High       | Medium    | Plateau selection, not peak; variance check       |
| 9   | Position limit breach             | 3, 5   | Medium     | High      | `clamp_order_size` is central; add debug logging  |
| 10  | Logger format incompatibility     | 0      | Low        | Medium    | Use Logger verbatim from sample; never modify     |

---

## Appendix B — Daily Pacing Suggestion

This assumes starting Wednesday evening and submitting Thursday morning.

**Wednesday evening (4 hours total, ~7pm–11pm):**

- Sprint 0: Tooling (1.5h)
- Sprint 1: EDA (1.5h)
- Sprint 2: Scaffolding (1h)

**Thursday morning (early, 2 hours, ~6am–8am):** _(if you have it)_

- Sprint 3: Osmium v1 (2h)

**Thursday late morning / afternoon (3.5 hours):**

- Sprint 4: Osmium tuning (1.5h)
- Sprint 5: Pepper Root v1 (2h)

**Thursday evening (3.5 hours):**

- Sprint 6: Pepper tuning (1.5h)
- Sprint 7: Integration + submission (1.5h) — **submit by ~4am ET, 2h before deadline**
- Sprint 8: Retro (0.5h)

_Adjust for your actual available windows. The plan is structured so that if you lose a block, you can collapse Sprints 4 and 6 (the tuning sprints) into "use the v1 defaults" and still submit something viable._

---

## Appendix C — Definition of Done

Round 1 is "done" when all of the following are true:

- [ ] Algorithm has been uploaded to IMC with at least 2 hours before the deadline.
- [ ] Platform has confirmed receipt (last-upload timestamp visible).
- [ ] The submitted algorithm, when run on IMC's in-app backtester, produces non-error output with non-zero PnL.
- [ ] You have a retro document capturing learnings.
- [ ] Your repo is committed and the code you submitted matches the code in your repo.
- [ ] You are no longer editing the submission.

Nothing else matters for Round 1's definition of done — not leaderboard position, not absolute PnL, not code beauty. If the checkboxes are checked, Round 1 is successful regardless of where the numbers land.
