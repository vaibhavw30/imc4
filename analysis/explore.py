"""Exploratory data analysis for Round 1.

Run from the repo root:

    python -m analysis.explore

Prints per-product distribution + dynamics statistics to stdout, and
saves diagnostic plots to analysis/plots/.

What to look for:
  - "mode (rounded int)" line tells you the fixed fair value of any
    stable product (calibrate OSMIUM_FAIR_VALUE from this).
  - "return autocorr" near zero across lags suggests a random walk
    (drifting product); strongly negative at lag 1 suggests
    mean-reversion.
  - "rolling std" gives a sense of how much wiggle room a passive
    quote should leave around fair value.
"""

from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless rendering — no DISPLAY needed

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analysis.load_data import load_all_days, split_by_product

PLOTS_DIR = Path(__file__).resolve().parent / "plots"
ROUND_NUM = 1


def _clean_valid(df: pd.DataFrame) -> pd.DataFrame:
    """Drop empty-book rows: the CSV writes mid_price = 0.0 when both bid_1
    and ask_1 are NaN. Treat those as missing, not as a real price of zero.
    """
    return df[df["mid_price"].notna() & (df["mid_price"] > 0)].copy()


def stats_for_product(df: pd.DataFrame) -> dict:
    """Compute distribution + dynamics statistics for one product across all days.

    Filters out empty-book rows (mid_price == 0). Returns are computed WITHIN
    each day to avoid spurious cross-day .diff() values.
    """
    df = df.sort_values(["day", "timestamp"]).copy()
    valid = _clean_valid(df)
    mid = valid["mid_price"]
    # Per-day diff so we don't take a return across day boundaries.
    returns = valid.groupby("day")["mid_price"].diff().dropna()
    spread = (valid["ask_price_1"] - valid["bid_price_1"]).dropna()

    counts = Counter(mid.round().astype(int).tolist())
    if counts:
        mode_value, mode_count = counts.most_common(1)[0]
    else:
        mode_value, mode_count = None, 0

    def autocorr(series: pd.Series, lag: int) -> float:
        if len(series) <= lag:
            return float("nan")
        return float(series.autocorr(lag=lag))

    rolling_std_100 = mid.rolling(100).std().dropna()

    return {
        "n_timesteps": int(len(df)),
        "n_valid": int(len(valid)),
        "n_dropped_empty_book": int(len(df) - len(valid)),
        "per_day_mean": {int(d): float(g["mid_price"].mean()) for d, g in valid.groupby("day")},
        "per_day_std": {int(d): float(g["mid_price"].std()) for d, g in valid.groupby("day")},
        "mid_mean": float(mid.mean()),
        "mid_std": float(mid.std()),
        "mid_min": float(mid.min()),
        "mid_max": float(mid.max()),
        "mid_median": float(mid.median()),
        "mid_mode": mode_value,
        "mid_mode_count": int(mode_count),
        "mid_mode_pct": float(100.0 * mode_count / len(mid)) if len(mid) else 0.0,
        "percentiles": {p: float(np.percentile(mid, p)) for p in (1, 5, 25, 50, 75, 95, 99)},
        "return_autocorr": {lag: autocorr(returns, lag) for lag in (1, 5, 10)},
        "rolling_std_100_mean": float(rolling_std_100.mean()) if len(rolling_std_100) else float("nan"),
        "rolling_std_100_max": float(rolling_std_100.max()) if len(rolling_std_100) else float("nan"),
        "spread_mean": float(spread.mean()) if len(spread) else float("nan"),
        "spread_median": float(spread.median()) if len(spread) else float("nan"),
        "spread_max": float(spread.max()) if len(spread) else float("nan"),
    }


def print_stats(product: str, stats: dict) -> None:
    print(f"\n=== {product} ===")
    print(f"  timesteps:           {stats['n_timesteps']} (valid: {stats['n_valid']}, "
          f"dropped empty-book: {stats['n_dropped_empty_book']})")
    print(f"  per-day mid mean:    " + ", ".join(
        f"day{d}={v:.1f}" for d, v in sorted(stats['per_day_mean'].items())))
    print(f"  per-day mid std:     " + ", ".join(
        f"day{d}={v:.2f}" for d, v in sorted(stats['per_day_std'].items())))
    print(f"  mid mean:            {stats['mid_mean']:.2f}")
    print(f"  mid std:             {stats['mid_std']:.2f}")
    print(f"  mid min/median/max:  {stats['mid_min']:.0f} / {stats['mid_median']:.1f} / {stats['mid_max']:.0f}")
    print(f"  mode (rounded int):  {stats['mid_mode']} (×{stats['mid_mode_count']}, {stats['mid_mode_pct']:.1f}%)")
    print(f"  percentiles:")
    for p, v in stats["percentiles"].items():
        print(f"    p{p:>2}: {v:.2f}")
    print(f"  return autocorr:")
    for lag, v in stats["return_autocorr"].items():
        print(f"    lag {lag:>2}: {v:+.4f}")
    print(f"  rolling std (100t):  mean={stats['rolling_std_100_mean']:.3f}  max={stats['rolling_std_100_max']:.3f}")
    print(f"  bid-ask spread:      mean={stats['spread_mean']:.2f}  median={stats['spread_median']:.1f}  max={stats['spread_max']:.0f}")


def _product_series(per_day: dict[int, pd.DataFrame], product: str) -> list[tuple[int, pd.DataFrame]]:
    """Per-day cleaned dataframes for a product (empty-book rows dropped)."""
    out = []
    for day, df in sorted(per_day.items()):
        sub = df[df["product"] == product].sort_values("timestamp")
        sub = _clean_valid(sub)
        if not sub.empty:
            out.append((day, sub))
    return out


def plot_mid_timeseries(per_day: dict[int, pd.DataFrame], product: str) -> None:
    series = _product_series(per_day, product)
    if not series:
        return
    fig, ax = plt.subplots(figsize=(12, 4))
    for day, sub in series:
        ax.plot(sub["timestamp"], sub["mid_price"], label=f"day {day}", linewidth=0.6)
    ax.set_title(f"{product} mid_price over time")
    ax.set_xlabel("timestamp")
    ax.set_ylabel("mid_price")
    ax.legend()
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / f"{product}_mid_timeseries.png", dpi=120)
    plt.close(fig)


def plot_mid_histogram(per_day: dict[int, pd.DataFrame], product: str) -> None:
    series = _product_series(per_day, product)
    if not series:
        return
    combined = pd.concat([s["mid_price"] for _, s in series]).dropna()
    if combined.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = max(20, min(80, int(combined.max() - combined.min()) + 1))
    ax.hist(combined, bins=bins)
    ax.set_title(f"{product} mid_price histogram (all days)")
    ax.set_xlabel("mid_price")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / f"{product}_mid_histogram.png", dpi=120)
    plt.close(fig)


def plot_spread_distribution(per_day: dict[int, pd.DataFrame], product: str) -> None:
    series = _product_series(per_day, product)
    if not series:
        return
    spreads = pd.concat([(s["ask_price_1"] - s["bid_price_1"]) for _, s in series]).dropna()
    if spreads.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(spreads, bins=range(int(spreads.min()), int(spreads.max()) + 2))
    ax.set_title(f"{product} bid-ask spread distribution")
    ax.set_xlabel("spread (ticks)")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / f"{product}_spread_histogram.png", dpi=120)
    plt.close(fig)


def plot_return_autocorr(per_day: dict[int, pd.DataFrame], product: str, max_lag: int = 30) -> None:
    series = _product_series(per_day, product)
    if not series:
        return
    # Per-day returns, then concat — avoids spurious cross-day .diff() values.
    returns = pd.concat([s["mid_price"].diff().dropna() for _, s in series])
    if len(returns) < max_lag + 1:
        return
    lags = list(range(1, max_lag + 1))
    acf = [returns.autocorr(lag=lag) for lag in lags]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(lags, acf)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title(f"{product} return autocorrelation (lags 1..{max_lag})")
    ax.set_xlabel("lag")
    ax.set_ylabel("autocorr")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / f"{product}_return_autocorr.png", dpi=120)
    plt.close(fig)


def main() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    per_day = load_all_days(ROUND_NUM)
    combined = pd.concat(per_day.values(), ignore_index=True)
    by_product = split_by_product(combined)

    summary: dict[str, dict] = {}
    for product, df in by_product.items():
        summary[product] = stats_for_product(df)
        print_stats(product, summary[product])
        plot_mid_timeseries(per_day, product)
        plot_mid_histogram(per_day, product)
        plot_spread_distribution(per_day, product)
        plot_return_autocorr(per_day, product)

    print("\n=== HEURISTIC: regime classification ===")
    for product, s in summary.items():
        per_day_means = list(s["per_day_mean"].values())
        per_day_stds = list(s["per_day_std"].values())
        day_drift = max(per_day_means) - min(per_day_means) if per_day_means else 0.0
        within_day_std = max(per_day_stds) if per_day_stds else 0.0

        # Three regimes worth distinguishing:
        #   STABLE — per-day std small AND day-to-day drift small.
        #   DAY-ANCHORED — per-day std small but day-to-day mean shifts a lot
        #                  (daily anchor moves; price is local around it).
        #   DRIFTING — per-day std itself is large (intra-day random walk).
        if within_day_std <= 15 and day_drift <= 50:
            verdict = "STABLE (fixed fair value)"
        elif within_day_std <= 50 and day_drift > 50:
            verdict = "DAY-ANCHORED (per-day fair value shifts)"
        else:
            verdict = "DRIFTING / WIDE-RANGE (intra-day std is large)"
        print(
            f"  {product:25s} → {verdict}\n"
            f"    within-day std (max across days): {within_day_std:.2f}\n"
            f"    day-to-day mean drift (range):    {day_drift:.2f}\n"
            f"    overall std:                      {s['mid_std']:.2f}\n"
            f"    p99 - p1 range:                   {s['percentiles'][99] - s['percentiles'][1]:.2f}\n"
            f"    lag-1 return autocorr:            {s['return_autocorr'][1]:+.3f}"
        )

    print(f"\nPlots written to: {PLOTS_DIR}")


if __name__ == "__main__":
    main()
