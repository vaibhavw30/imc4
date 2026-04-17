# IMC Prosperity 4 — Round 1

Algorithmic trading bot for the [IMC Prosperity 4](https://prosperity.imc.com/) competition.

## Project overview

IMC Prosperity is a 5-round algorithmic trading competition. Each round, you submit a Python `Trader` class whose `run(state)` method is invoked every timestep against a synthetic order book populated by bots. Orders live for one timestep only, and exceeding a product's position limit cancels all your orders for that product.

**Round 1** trades two products:

| Product | Behavior | Analog (Prosperity 3) |
|---|---|---|
| `ASH_COATED_OSMIUM` | Stable, fixed fair value | Rainforest Resin |
| `INTARIAN_PEPPER_ROOT` | Drifting / random walk | Kelp |

This repo holds the local development setup: data exploration, baseline strategies, a backtester, and a path to the hosted visualizer. **The strategies here are deliberately simple baselines** — get the pipeline working end-to-end, then iterate.

## Setup

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This installs `prosperity4btest` (from PyPI), pandas, numpy, and matplotlib.

## 1. Run EDA first

Always look at the data before tweaking strategy params.

```bash
python -m analysis.explore
```

This prints per-product stats and writes plots to `analysis/plots/`. **What to look for:**

- **Mode of the rounded mid-price** for `ASH_COATED_OSMIUM` — this is the fixed fair value. Update `OSMIUM_FAIR_VALUE` in `algo/strategies/osmium.py` if it isn't 10000.
- **Return autocorrelation at lag 1** for `INTARIAN_PEPPER_ROOT` — near zero confirms a random walk; strongly negative would suggest mean-reversion (and a different strategy).
- **Bid-ask spread distribution** — informs how tight `PEPPER_MIN_EDGE` and `PEPPER_BAND_WIDTH` should be.
- **Mid-price histogram** — a sharp spike at one integer = stable; broad distribution = drifting.

The script ends with a one-line per-product STABLE/DRIFTING verdict based on the mode share and standard deviation.

## 2. Run a backtest

```bash
./run_backtest.sh
```

Output is timestamped under `logs/`. Forward extra flags to the underlying CLI:

```bash
./run_backtest.sh --match-trades worse   # pessimistic fill model
./run_backtest.sh --print                # show stdout in addition to the log file
```

The script sets `PYTHONPATH=.` so the `from algo.* import ...` lines in `algo/trader.py` resolve correctly when `prosperity4btest` imports the file.

## 3. Visualize

The log file written by the backtester is consumed by the hosted visualizer at <https://prosperity.equirag.com/>:

1. Drag the latest `logs/run_*.log` file onto the page.
2. Inspect: per-product PnL, position over time, fills, and your own orders relative to the order book.
3. If the visualizer can't parse the file, the Logger format has drifted from what it expects — `algo/logger.py` was copied verbatim from `nabayansaha/imc-prosperity-4-backtester/sample.py`, so any drift means the upstream sample changed and you should re-fetch it.

## 4. Iterate on strategy

The two files you'll edit most:

- `algo/strategies/osmium.py` — stable-product market maker. Constants at the top (`OSMIUM_FAIR_VALUE`, `OSMIUM_MAKE_EDGE`, `OSMIUM_BASE_QUOTE_SIZE`, `OSMIUM_POSITION_LIMIT`).
- `algo/strategies/pepper_root.py` — drifting-product market maker with a no-trade band. Constants: `PEPPER_MIN_EDGE`, `PEPPER_BAND_WIDTH`, `PEPPER_MAX_EXTRA_BAND`, `PEPPER_BASE_QUOTE_SIZE`, `PEPPER_WALL_VOLUME`, `PEPPER_ROOT_POSITION_LIMIT`.

After each change: `./run_backtest.sh` → upload to the visualizer → eyeball PnL and position behavior.

Shared utilities under `algo/utils/` (`order_book.py`, `position.py`) are designed to be reused across all five rounds. Add product-specific helpers as new files in `algo/utils/` rather than bloating the strategy files.

## 5. Submission checklist

Before uploading to the IMC platform:

- [ ] `OSMIUM_FAIR_VALUE` calibrated from EDA mode (not the placeholder).
- [ ] Position limits verified against the official Round 1 problem statement (sample.py says **80** for both — different from P3's 50).
- [ ] Backtest PnL is positive on each of `day -2`, `day -1`, `day 0`.
- [ ] Visualizer log looks clean: no error spam, position respects limits, quotes look sane.
- [ ] **Flatten the algo into a single `trader.py`** (see [Architecture notes](#architecture-notes)).
- [ ] One final local backtest after flattening — make sure the flattened file produces the same orders as the modular version.

## Architecture notes

```
algo/
├── trader.py               # Entry point — what gets uploaded
├── logger.py               # jmerle Logger (verbatim, do NOT modify)
├── strategies/
│   ├── base.py             # Strategy ABC
│   ├── osmium.py           # ASH_COATED_OSMIUM market maker
│   └── pepper_root.py      # INTARIAN_PEPPER_ROOT market maker
└── utils/
    ├── order_book.py       # best_bid, best_ask, mid_price, wall_mid
    └── position.py         # clamp_order_size, inventory_skew

analysis/
├── load_data.py            # CSV loaders
└── explore.py              # `python -m analysis.explore`
```

**Why one strategy per file?** Round 2+ adds more products. A flat per-product file scales; a god-object Trader doesn't.

**What is `wall_mid`?** Designated market makers post fat quotes that hug fair value much more tightly than retail noise at the top of the book. `wall_mid` finds the deepest level on each side (filtered by a min-volume threshold) and returns their midpoint — a less-noisy fair-value estimate than the raw best-bid/best-ask midpoint. Falls back to `mid_price` if no level meets the threshold.

**Why does Pepper have a no-trade band?** Drifting products with tight spreads punish overtrading — the bot counterparty is informed, so crossing the spread for less than `PEPPER_MIN_EDGE` ticks of edge tends to bleed PnL. Sitting out a tight tick is often correct.

## Known issues / TODOs

- [ ] **Fair value placeholder.** `OSMIUM_FAIR_VALUE = 10_000` is a guess from sample.py. Calibrate from `python -m analysis.explore` output before submitting.
- [ ] **Position limits.** Set to **80** based on `sample.py`. Verify against the official Round 1 problem statement — the platform will silently cancel all your orders for a product if you exceed its limit.
- [ ] **Single-file submission.** IMC's UI accepts only one Python file. Before submitting, manually concatenate `algo/logger.py` + `algo/utils/*` + `algo/strategies/*` + `algo/trader.py` into a single file and drop the `from algo.* import ...` lines. (TODO: write `scripts/flatten.py` to automate this.)
- [ ] **No persisted state.** `traderData` is set to `""` each tick. If a future strategy needs cross-tick memory (rolling fair-value smoothing, signal accumulators), serialize/deserialize it through `state.traderData`.
- [ ] **No tests, no CI.** Intentional for Round 1. Add when the strategy logic gets non-trivial.
