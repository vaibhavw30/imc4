# Product Requirements Document

## IMC Prosperity 4 — Round 1 Algorithmic Trading System

**Document version:** 1.0
**Author:** [You]
**Last updated:** April 16, 2026
**Status:** Draft / pre-implementation

---

## 1. Executive Summary

This document specifies the requirements for a Python-based algorithmic trading system designed to compete in **Round 1 of IMC Prosperity 4**. The system will trade two virtual products — `ASH_COATED_OSMIUM` and `INTARIAN_PEPPER_ROOT` — against bot market participants on IMC's simulated trading platform, with the goal of maximizing PnL (measured in the in-game currency XIRECS/SeaShells) by the Round 1 deadline.

The competition runs April 14–30, 2026, across five sequential rounds. Round 1 is the foundation: the products traded in this round persist through all subsequent rounds, meaning a robust Round 1 strategy compounds value over the remaining two weeks of the competition. A poorly-built Round 1 strategy is not just a single-round loss — it leaks PnL every round until it is fixed.

This PRD is scoped to Round 1 only. Rounds 2–5 will be addressed in follow-on PRDs as each round's products are revealed.

---

## 2. Background & Context

### 2.1 What is Prosperity?

Prosperity is IMC's annual global trading competition for STEM students, now in its fourth iteration. Teams develop Python algorithms that trade fictional products on a simulated exchange. Each round, the algorithm is re-submitted and re-evaluated against a fresh marketplace of bot traders. The sum of PnL across all rounds determines the final leaderboard.

Each round also includes a **manual challenge** — a one-shot puzzle submitted via the web UI. The manual and algorithmic tracks are scored independently. This PRD covers only the algorithmic track.

### 2.2 Why Round 1 matters disproportionately

Three structural reasons:

1. **Products persist.** Round 1 products keep trading in Rounds 2, 3, 4, and 5. A strategy that earns 5,000 XIRECS per round earns 25,000 total; one that loses 5,000 per round loses 25,000 total. The multiplier on Round 1 work is 5x.
2. **Round 1 is the teaching round.** Historically, IMC uses Round 1 to introduce a "stable fair-value" product and a "drifting random-walk" product. The patterns are well-understood; mistakes here are avoidable with discipline.
3. **Infrastructure built in Round 1 carries forward.** The backtester integration, logging, position tracking, and code structure built now will be reused for the more complex rounds (baskets, options, conversions). Time invested in a clean foundation pays off repeatedly.

### 2.3 Prior art and reference material

The primary reference for this project is the **Frankfurt Hedgehogs' writeup** from Prosperity 3 (2nd place globally, 12,000+ teams competing). Key insights adopted from their work:

- **Wall Mid as fair-value proxy.** Deep-liquidity quotes in the order book come from designated market makers quoting close to the true price. Averaging the deepest bid and ask yields a cleaner fair-value estimate than simple mid-price, which is distorted by small-volume overbidders and undercutters.
- **Structural understanding before optimization.** Do not apply statistical tooling (z-scores, moving averages, ML models) without a first-principles reason they should work. Most "edges" found by blind backtesting are noise.
- **Simplicity wins.** Their final strategies for the Round 1 analogs (Rainforest Resin, Kelp) were conceptually trivial. The edge came from correctly identifying product behavior, using wall_mid, and respecting position limits — not from algorithmic sophistication.
- **Landscape stability over peak performance.** When grid-searching parameters, prefer the flat plateau of consistent performance over a single peak that maximizes historical PnL. The peak is usually overfit.

Additional context from public Discord chatter during Round 1 of Prosperity 4 suggests:

- Osmium is behaving as the stable product; PnL caps for most teams in the 2–4k range, with top performers reaching ~10k.
- Pepper Root is behaving as the drifting product; most teams are _losing_ money on it due to overtrading; top PnLs are claimed in the 7–8k range but many are likely overfit or fabricated.
- A strong team's reported PnL split is roughly 33% Osmium / 67% Pepper Root, indicating Pepper has higher ceiling if traded conservatively.

### 2.4 Competition timeline

| Milestone                              | Date                                       |
| -------------------------------------- | ------------------------------------------ |
| Tutorial round opens                   | March 16, 2026                             |
| Registration deadline                  | April 14, 2026, 12:00 CEST                 |
| Round 1 starts                         | April 14, 2026, 12:00 CEST                 |
| **Round 1 ends / submission deadline** | **April 17, 2026, 12:00 CEST (~06:00 ET)** |
| Round 2 starts                         | April 17, 2026                             |
| Competition ends                       | April 30, 2026, 12:00 CEST                 |

The last algorithm uploaded before the Round 1 deadline is the one evaluated. Iterative submissions are allowed and encouraged.

---

## 3. Goals & Non-Goals

### 3.1 Goals (Round 1)

**Primary:**

- Submit a working, profitable algorithm for Osmium and Pepper Root by the Round 1 deadline.
- Achieve consistent positive PnL on at least Osmium across all three historical days in local backtests.
- Build scaffolding (backtester integration, logger, data exploration, strategy base class, position tracker) that extends cleanly to Rounds 2–5.

**Secondary:**

- Break into the top 25% of the Round 1 leaderboard (a rough proxy for "we did not embarrass ourselves").
- Produce a clean, reviewable codebase that can be handed off or shared with teammates if applicable.
- Develop reusable intuition about Prosperity market microstructure (fills, spreads, bot behavior) that informs later rounds.

**Nice-to-have:**

- A no-trade band on Pepper Root that successfully turns it from a loss-making product into a small positive contributor.
- A parameter grid search that finds a stable plateau (not a peak) of performance.

### 3.2 Non-goals (explicitly out of scope)

- **Winning Round 1 outright.** The top of the leaderboard is contested by teams with years of Prosperity experience and often heavy preparation. The goal is competitive performance and learning foundation, not first place.
- **Sophisticated ML / regression models.** Per the Hedgehogs: Round 1 products are not predictable at a meaningful level. Regression is planned for Rounds 2 (basket spreads), 3 (volatility smile), and 4 (macaron-equivalent features) — not Round 1.
- **Hard-coding against bot behavior.** Some teams exploit reproducible bot actions. IMC banned this mid-competition in Prosperity 3; the risk/reward is bad.
- **Multi-file submission infrastructure.** If IMC requires a single flat file for submission, we will inline the package at submission time — not build a build system.
- **Production-grade test suites, CI/CD, monitoring dashboards.** This is a two-week competition, not a product launch.
- **Manual challenge for Round 1.** Handled separately; not in this PRD.

### 3.3 Explicit anti-goals (things that would indicate we went wrong)

- Spending more than 4 hours on a single parameter-tuning session without re-examining the underlying strategy.
- Submitting a strategy whose PnL is wildly different between local backtest and platform backtest (indicates hidden overfit or simulation mismatch).
- Writing more than ~500 lines of strategy code in total for Round 1 (if we're writing that much, we're overengineering).
- Using any market-data library beyond `pandas` and `numpy` before the final submission.

---

## 4. User Persona & Use Cases

### 4.1 Primary user: the competitor (me)

Intermediate Python skills, basic trading concepts, first Prosperity competition. Works on a macOS laptop with system Python 3. Limited time budget (approximately 2–3 hours per day across the competition window). Priorities: learn, compete respectably, not embarrass themselves, build transferable skills.

### 4.2 Use cases

**UC-1: Data exploration**

> As a competitor, I want to quickly visualize the price distribution and volatility of each Round 1 product so that I can confirm which is stable and which is drifting, and calibrate fair-value parameters from real data.

**UC-2: Strategy iteration**

> As a competitor, I want to modify a single strategy file and re-run a local backtest in under 30 seconds so I can rapidly iterate on edge sizing, skew, and band-width parameters without context-switching.

**UC-3: Visual debugging**

> As a competitor, I want to see my fills overlaid on the order book in a chart so that I can identify when my algorithm missed profitable opportunities or entered bad fills.

**UC-4: Parameter sweeping**

> As a competitor, I want to run a batch of backtests across parameter combinations and see the PnL surface so that I can identify a stable plateau rather than a single peak.

**UC-5: Submission**

> As a competitor, I want to produce a single, platform-compatible Python file from my modular codebase with one command so that I can submit without manual copy-paste errors.

**UC-6: Cross-round extensibility**

> As a competitor in Round 2 (future), I want to add a new product strategy (for baskets) by creating a new file in `algo/strategies/` and registering it in the main Trader class, without rewriting the trading loop or utilities.

---

## 5. Product Definition

### 5.1 System overview

The system consists of five logical components:

1. **Trading algorithm** — the `Trader` class and per-product strategy modules. This is what gets uploaded to IMC's platform.
2. **Market-data utilities** — shared helpers for interpreting order books (wall_mid, best bid/ask, spread).
3. **Position-tracking utilities** — shared helpers for enforcing position limits and computing inventory skew.
4. **Logger** — jmerle-compatible log emission so that backtest output can be rendered in the community visualizer.
5. **Analysis tooling** — data-loading functions and exploration scripts that read the Data Capsule CSVs and produce summary statistics and charts.

### 5.2 Component specifications

#### 5.2.1 `Trader` class (entry point)

- Implements the IMC-specified interface: `run(state: TradingState) -> tuple[dict[str, list[Order]], int, str]`.
- Delegates to per-product `Strategy` instances, one per symbol traded.
- Wraps each strategy's `run()` in a try/except to prevent a failure in one product from zeroing out the other.
- Emits a compressed log line at the end of every `run()` call via the Logger.
- Returns `conversions=0` and `trader_data=""` for Round 1 (no conversions yet, no cross-tick state needed).

#### 5.2.2 Per-product strategy modules

Each strategy inherits from an abstract `Strategy` base class with a single `run(state) -> list[Order]` method. Two concrete strategies for Round 1:

**`OsmiumStrategy`** (stable product):

- Fixed fair-value constant (calibrated from data; placeholder value pending EDA).
- Takes any asks below fair value, any bids above fair value, up to position-limit constraints.
- Makes passive quotes at `fair_value - 1` (bid) and `fair_value + 1` (ask).
- Skews quote sizes based on current inventory: if long, quote more on the ask side; if short, quote more on the bid side.
- Parameters: `fair_value: int`, `position_limit: int`, `max_order_size: int`.

**`PepperRootStrategy`** (drifting product):

- Computes fair value each tick as `wall_mid(order_depth)`; falls back to `mid_price` if wall_mid is unavailable.
- Applies a **no-trade band** of width `min_edge` around fair value — does not quote if the expected edge is less than this threshold.
- Makes passive quotes at `fair_value - band_width` (bid) and `fair_value + band_width` (ask), where `band_width >= min_edge`.
- Same inventory-skew logic as Osmium.
- Parameters: `position_limit: int`, `min_edge: int`, `band_width: int`, `max_order_size: int`.

#### 5.2.3 `wall_mid` utility

```
def wall_mid(order_depth, min_volume: int = 15) -> float | None:
    """Midpoint of the deepest bid and deepest ask in the order book.

    The deepest levels are assumed to come from designated market makers
    quoting near the true fair value. This is a more robust fair-value
    proxy than simple mid-price, which is distorted by small-volume
    overbidders and undercutters.

    Returns None if no level meets min_volume on either side; caller
    should fall back to mid_price.
    """
```

#### 5.2.4 Position tracker

```
def clamp_order_size(position: int, desired_qty: int, limit: int) -> int:
    """Return the actual quantity submittable without breaching limit."""
```

Handles both buy (positive) and sell (negative) quantities. Never returns a value that would cause `|position + qty| > limit`.

#### 5.2.5 Logger

The jmerle-compatible `Logger` class, pasted verbatim from the backtester's `sample.py`. Emits a sentinel-prefixed, base64-compressed JSON payload containing timestamp, state, orders, conversions, trader data, and printed output. The community visualizer at `prosperity.equirag.com` parses this format.

**Do not modify the Logger.** Its format is constrained by the visualizer. Modifications silently break visualization.

#### 5.2.6 Data loader

```
def load_prices(round_num: int, day: int) -> pd.DataFrame
def load_all_days(round_num: int) -> dict[int, pd.DataFrame]
def split_by_product(df: pd.DataFrame) -> dict[str, pd.DataFrame]
```

Handles the IMC CSV format: semicolon-separated, columns include `day`, `timestamp`, `product`, `bid_price_1..3`, `bid_volume_1..3`, `ask_price_1..3`, `ask_volume_1..3`, `mid_price`, `profit_and_loss`. Located in `data/prices_round_1_day_{-2,-1,0}.csv`.

#### 5.2.7 Exploration script

Runnable as `python -m analysis.explore`. Produces:

- Stdout summary of each product's mean, std, min, max, median, mode, percentiles (1/5/25/50/75/95/99), modal frequency, return autocorrelations at lags 1/5/10, rolling 100-tick volatility.
- Saved PNGs in `analysis/plots/` of: mid-price time series (per product per day), mid-price histogram (per product), spread distribution (per product), return autocorrelation (per product).
- A closing summary classifying each product as "stable" or "drifting" based on modal frequency and rolling volatility.

### 5.3 Repository structure

```
.
├── algo/
│   ├── __init__.py
│   ├── trader.py
│   ├── logger.py
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── osmium.py
│   │   └── pepper_root.py
│   └── utils/
│       ├── __init__.py
│       ├── order_book.py
│       └── position.py
├── analysis/
│   ├── load_data.py
│   ├── explore.py
│   └── plots/
│       └── .gitkeep
├── data/
│   ├── prices_round_1_day_-2.csv
│   ├── prices_round_1_day_-1.csv
│   └── prices_round_1_day_0.csv
├── logs/
├── docs/
│   ├── PRD.md
│   └── SPRINT_PLAN.md
├── .gitignore
├── requirements.txt
├── run_backtest.sh
└── README.md
```

---

## 6. Technical Requirements

### 6.1 Stack

| Layer               | Choice                            | Justification                                                   |
| ------------------- | --------------------------------- | --------------------------------------------------------------- |
| Language            | Python 3.10+                      | Required by IMC platform; matches `prosperity4btest` dependency |
| Virtual environment | `venv` (stdlib)                   | Zero-dependency, works with macOS system Python                 |
| Data manipulation   | `pandas`                          | Standard for CSV analysis                                       |
| Numerics            | `numpy`                           | Required by pandas, useful for rolling statistics               |
| Plotting            | `matplotlib`                      | Stable, no extra dependencies for static plots                  |
| Backtester          | `prosperity4btest` (PyPI)         | Fork of jmerle's Prosperity 3 backtester, updated for P4        |
| Visualizer          | `prosperity.equirag.com` (hosted) | Community standard, consumes jmerle logger format               |

### 6.2 Platform constraints (from IMC)

- Algorithm runs in a sandboxed Python environment on IMC's servers.
- `Trader.run()` is called once per simulated timestep.
- Orders returned live for exactly one timestep — they are cleared at the start of the next tick.
- Position limits are enforced: submitting orders that would breach the limit causes _all_ orders for that product to be rejected for that tick. This is catastrophic; the position tracker must prevent it.
- Round 1 position limit: **TBD from the problem statement** (default assumption: 50). Must be verified before submission.
- `traderData` is a string that persists across ticks. For Round 1, we don't use it.
- `conversions` is an integer; relevant from Round 4 onward. Set to 0 for Round 1.

### 6.3 Non-functional requirements

- **Backtest runtime:** single-day backtest should complete in under 60 seconds on a typical laptop. Enables fast iteration.
- **Submission file size:** the uploaded file must stay within IMC's size limit (historically generous, but inlined helpers should not balloon the file beyond ~3000 lines).
- **Determinism:** given the same historical data and the same strategy parameters, the local backtester must produce identical PnL across runs. Relied upon for parameter tuning.
- **No external network calls at runtime:** the algorithm must not rely on external APIs, file reads beyond what IMC provides, or anything else unavailable in the sandbox.

### 6.4 Dependencies

All dependencies pinned loosely (minor version acceptable) in `requirements.txt`:

```
prosperity4btest
pandas
numpy
matplotlib
```

No test frameworks, no linting tools, no formatting tools. We are optimizing for time-to-submit.

---

## 7. Success Metrics

### 7.1 Quantitative

| Metric                                                      | Target             | Stretch       |
| ----------------------------------------------------------- | ------------------ | ------------- |
| Osmium local backtest PnL (per day, averaged across 3 days) | > 2,000            | > 4,000       |
| Pepper Root local backtest PnL (per day, averaged)          | > 0 (non-negative) | > 3,000       |
| Combined Round 1 platform PnL                               | > 5,000            | > 10,000      |
| Variance of PnL across the 3 backtested days                | < 30% of mean      | < 15% of mean |
| Final leaderboard percentile after Round 1                  | Top 50%            | Top 25%       |

### 7.2 Qualitative

- Code is readable without comments by someone familiar with the `datamodel` module.
- Adding a new product strategy for Round 2 requires creating one new file and modifying `Trader.__init__` by adding a single dict entry.
- The exploration script's stdout output makes it immediately obvious which product is stable and which is drifting, without having to view plots.
- Backtester logs render cleanly in the visualizer on first try.

### 7.3 Anti-metrics (what would indicate failure)

- A backtest PnL > 20k on any single day — this is almost certainly overfitting to a data artifact.
- Position limit breaches in any backtest (visible as cancelled orders in logs).
- Python exceptions during backtest runs.
- A strategy whose PnL on day `-2` differs by more than 2x from day `0` — indicates sensitivity to initial conditions that will not generalize.

---

## 8. Risks & Mitigations

### 8.1 Risk: Logger format drift

**Description:** If the `Logger` class is not byte-identical to what the visualizer expects, logs will silently fail to render. Time lost debugging a non-code issue.

**Mitigation:** Copy the Logger verbatim from the backtester's `sample.py`. Do not modify. Verify by running the empty starter strategy and confirming it renders in the visualizer before writing any strategy logic.

### 8.2 Risk: Backtester simulation ≠ platform simulation

**Description:** The local backtester cannot perfectly replicate bot behaviors on IMC's platform. A strategy that performs well locally may underperform on the platform (or vice versa). Hedgehogs specifically noted this for products sensitive to bot interaction.

**Mitigation:** After each significant strategy change, run both the local backtest (for fast feedback) _and_ the platform's built-in backtester (for validation). Do not optimize purely for local or purely for platform score — use both as cross-checks.

### 8.3 Risk: Overfitting to 3 days of data

**Description:** Only 3 days of historical data are provided. Parameter tuning can easily find values that look good on these 3 days but fail on the 4th day IMC uses for evaluation.

**Mitigation:** Prefer the flat plateau of parameter space over the peak. When grid-searching, pick the parameters at the center of a region of stable-good performance, not at the single-best point. Treat the 3 days as independent samples — if a strategy wins on all 3 with similar PnL, it's robust; if it wins big on day `-2` and loses on day `0`, it's overfit.

### 8.4 Risk: Position limit breach cascades

**Description:** A bug in the position tracker could cause all orders for a product to be rejected on a given tick, silently zeroing out fills.

**Mitigation:** The `clamp_order_size` utility is a single function with a clear contract. Test it manually in a REPL with edge cases (position at limit, near limit, zero). Add a runtime log line whenever it clamps a non-zero amount — easy to grep for during debugging.

### 8.5 Risk: Submission deadline crunch

**Description:** Round 1 ends at 12:00 CEST on April 17 (06:00 ET). Uploading at 05:59 ET leaves no margin for a last-minute bug. In Prosperity 3, several teams missed evaluation due to deadline issues.

**Mitigation:** Target "final" submission 2+ hours before deadline. Treat the last 2 hours as buffer for post-submission verification (check the platform confirms receipt, run one more sanity backtest to ensure the file is valid).

### 8.6 Risk: Single-file submission requirement

**Description:** IMC may require a single flat Python file for upload. The modular package structure won't work as-is.

**Mitigation:** Verify the submission form's requirements on day 1 of Round 1. If single-file is required, write a simple `build.py` script that concatenates the modules in the correct order into `trader_submission.py`. This is a 30-line script; budget 1 hour for it if needed.

### 8.7 Risk: Pepper Root negative PnL

**Description:** Per Discord chatter, most teams are losing money on Pepper Root. Our baseline may do the same.

**Mitigation:** The `min_edge` no-trade band is specifically designed for this. If even with a wide band Pepper is negative, the fallback is to submit an empty strategy for Pepper (`return []` from `run()`) — a zero-PnL strategy beats a negative-PnL strategy. This is a legitimate move per the Hedgehogs' "do nothing is a baseline" principle.

### 8.8 Risk: Time sink on tooling

**Description:** Setting up backtester, visualizer, logger, and plots can consume a full day if something goes wrong with environment configuration.

**Mitigation:** Budget the tooling setup as its own sprint (Sprint 0 in the sprint plan). If it isn't working after 3 hours, pause strategy work and diagnose tooling first. Keep the known-good empty starter strategy as a "is my pipeline working?" test.

---

## 9. Open Questions

To be resolved in Sprint 0 (data exploration and tooling setup):

1. **What is the actual fixed fair value of Osmium?** (Resolved by `python -m analysis.explore`; look at the mode of mid-price distribution.)
2. **What is the actual position limit for each Round 1 product?** (Check IMC's Round 1 problem statement; 50 is the assumed default.)
3. **Does the IMC submission form accept multi-file uploads or only single files?** (Check the platform directly before writing more code.)
4. **What is the bid-ask spread distribution for Pepper Root?** (Determines realistic bounds for `min_edge` and `band_width` parameters.)
5. **Is there meaningful autocorrelation in Pepper Root returns?** (If yes — negative autocorrelation at lag 1 — mean reversion is a viable addition. If no, stick to pure market making.)

To be resolved later (Rounds 2–5):

- What products will Round 2 introduce? (Historically: basket/ETF analogs.)
- Does Round 3 introduce options? (Historically yes; need Black-Scholes.)
- Does Round 4 introduce conversions and hidden taker bots? (Historically yes.)
- Does Round 5 reveal trader IDs? (Historically yes.)

---

## 10. Appendix

### 10.1 Glossary

- **XIRECS** — Prosperity 4's in-game currency (equivalent to SeaShells in Prosperity 3).
- **PnL** — Profit and Loss, measured in XIRECS.
- **Wall Mid** — Midpoint of the deepest-volume bid and deepest-volume ask in the order book, used as a robust fair-value proxy.
- **Take (aggressive order)** — An order that crosses the existing book and executes immediately.
- **Make (passive order)** — An order that rests on the book waiting for a counterparty.
- **Edge** — The difference between your trade price and your estimated fair value. Positive edge = profitable trade.
- **Position limit** — The maximum absolute position (long or short) you may hold in a given product. Breaches cause order rejection.
- **Inventory skew** — A measure of how lopsided your current position is relative to the limit, used to bias quotes toward flattening.
- **No-trade band** — A range around fair value in which the strategy does not quote, to avoid low-edge trades that are net-negative after spread costs.
- **Mean reversion** — A price pattern in which deviations from a mean tend to revert; tradable via "buy low, sell high" around a rolling average.

### 10.2 Key reference documents

- Frankfurt Hedgehogs Prosperity 3 writeup: `github.com/TimoDiehm/imc-prosperity-3`
- jmerle's Prosperity 3 backtester: `github.com/jmerle/imc-prosperity-3-backtester`
- Prosperity 4 backtester (fork): `github.com/nabayansaha/imc-prosperity-4-backtester`
- Prosperity visualizer: `prosperity.equirag.com`
- Prosperity 4 wiki and platform: `prosperity.imc.com`

### 10.3 Change log

| Version | Date           | Changes                          |
| ------- | -------------- | -------------------------------- |
| 1.0     | April 16, 2026 | Initial draft pre-implementation |
