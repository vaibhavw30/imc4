"""Sprint-3 diagnostic: characterize R2-vs-R1 Pepper regime difference.

Pure observation. No strategy changes. Subcommands cover Tasks 1-4 of the
Sprint 3 brief.

Usage (from repo root, PYTHONPATH=.):
    python3 analysis/r2_diagnostic.py baseline   # Task 1
    python3 analysis/r2_diagnostic.py drift      # Task 2
    python3 analysis/r2_diagnostic.py ema        # Task 3
    python3 analysis/r2_diagnostic.py decompose  # Task 4
    python3 analysis/r2_diagnostic.py all        # everything, into stdout
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analysis.parse_log import (
    extract_own_trades,
    extract_positions_and_books,
    fill_summary,
    parse_activities_final_pnl,
    split_sections,
)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
R1_DIR = DATA / "ROUND_1"
R2_DIR = DATA / "ROUND_2"

R1_DAYS = (-2, -1, 0)
R2_DAYS = (-1, 0, 1)
PRODUCTS = ("ASH_COATED_OSMIUM", "INTARIAN_PEPPER_ROOT")

# Canonical R1/R2 backtest logs (wall_volume=12, --match-trades worse --merge-pnl).
# Identified from PnL matching the Sprint 2 brief.
R1_LOG = REPO / "backtests" / "2026-04-20_01-11-43.log"
R2_LOG = REPO / "backtests" / "2026-04-20_01-11-55.log"

# EMA overlay params — MUST match algo/strategies/pepper_root.py.
EMA_ALPHA = 0.005
DRIFT_THRESHOLD = 8.0


def load_day(round_num: int, day: int) -> pd.DataFrame:
    data_dir = R1_DIR if round_num == 1 else R2_DIR
    path = data_dir / f"prices_round_{round_num}_day_{day}.csv"
    return pd.read_csv(path, sep=";")


def per_product_series(df: pd.DataFrame, product: str) -> pd.DataFrame:
    sub = df[df["product"] == product].sort_values("timestamp").reset_index(drop=True)
    # Source CSV writes mid_price=0 when the book is degenerate (both sides
    # empty). The live strategy returns no orders on such ticks, so we filter
    # them out of price statistics — otherwise they inflate std and drawup by
    # ~10,000 per day and produce nonsense stats.
    sub = sub[sub["mid_price"] > 1].reset_index(drop=True)
    return sub


# ---------- Task 1: baseline comparison ----------

def baseline_row(round_num: int, day: int, product: str) -> dict:
    df = load_day(round_num, day)
    s = per_product_series(df, product)
    mids = s["mid_price"].astype(float)
    bb = s["bid_price_1"].astype(float)
    ba = s["ask_price_1"].astype(float)
    spread = (ba - bb)
    spread_valid = spread.dropna()
    drift = float(mids.iloc[-1] - mids.iloc[0]) if len(mids) else float("nan")
    n_nan = int(mids.isna().sum())
    return {
        "round": f"R{round_num}",
        "day": day,
        "product": product.split("_")[-1].capitalize() if product == "INTARIAN_PEPPER_ROOT" else "Osmium",
        "ticks": len(s),
        "mean": round(float(mids.mean()), 2),
        "std": round(float(mids.std(ddof=0)), 2),
        "min": float(mids.min()),
        "max": float(mids.max()),
        "drift": round(drift, 1),
        "spread_mean": round(float(spread_valid.mean()), 2),
        "spread_med": int(spread_valid.median()),
        "spread_p75": int(spread_valid.quantile(0.75)),
        "nan_ticks": n_nan,
    }


def run_baseline() -> list[dict]:
    rows = []
    for r, days in ((1, R1_DAYS), (2, R2_DAYS)):
        for d in days:
            for p in PRODUCTS:
                rows.append(baseline_row(r, d, p))
    return rows


def print_baseline(rows: list[dict]) -> str:
    buf: list[str] = []
    buf.append("| Round | Day | Product | Ticks | Mean | Std | Drift | Spread_med | Spread_p75 |")
    buf.append("|---|---:|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        buf.append(
            f"| {r['round']} | {r['day']} | {r['product']} | {r['ticks']} | "
            f"{r['mean']:,.1f} | {r['std']:.1f} | {r['drift']:+,.0f} | "
            f"{r['spread_med']} | {r['spread_p75']} |"
        )
    return "\n".join(buf)


# ---------- Task 2: intra-day drift ----------

def drift_characterize(mids: pd.Series, window: int = 500) -> dict:
    """Given a price series, compute:
      - fraction of ticks in upward/downward/flat drift relative to rolling mean
      - direction-flip count (transitions of the sign)
    A tick is 'flat' if |mid - rolling_mean| < 1 tick (i.e., below noise floor).
    """
    m = mids.astype(float).reset_index(drop=True)
    rm = m.rolling(window=window, min_periods=1).mean()
    diff = m - rm
    # Treat |diff| < 1 tick as flat to avoid counting pure noise as a drift flip.
    dir_sign = diff.apply(lambda x: 1 if x > 1 else (-1 if x < -1 else 0))
    total = len(dir_sign)
    frac_up = (dir_sign == 1).sum() / total
    frac_dn = (dir_sign == -1).sum() / total
    frac_flat = (dir_sign == 0).sum() / total

    # Direction flips = transitions from +1 to -1 or -1 to +1 (ignoring 0).
    prev = 0
    flips = 0
    for x in dir_sign:
        if x == 0:
            continue
        if prev != 0 and x != prev:
            flips += 1
        prev = x
    # Start-to-end net drift
    net = float(m.iloc[-1] - m.iloc[0])
    # Peak-to-trough excursion (max drawup and drawdown from running max/min)
    running_max = m.cummax()
    running_min = m.cummin()
    max_drawdown = float((m - running_max).min())
    max_drawup = float((m - running_min).max())
    return {
        "ticks": total,
        "net_drift": round(net, 1),
        "frac_up": round(frac_up * 100, 1),
        "frac_dn": round(frac_dn * 100, 1),
        "frac_flat": round(frac_flat * 100, 1),
        "dir_flips": flips,
        "max_drawup": round(max_drawup, 1),
        "max_drawdown": round(max_drawdown, 1),
    }


def run_drift() -> list[dict]:
    # Focus: Pepper on R1 d -2, R1 d -1 (winning), R2 d 0, R2 d 1 (losing).
    # Also include R2 d -1 (R2's positive day) and R1 d 0 for completeness.
    targets = [
        (1, -2), (1, -1), (1, 0),
        (2, -1), (2, 0), (2, 1),
    ]
    rows = []
    for r, d in targets:
        df = load_day(r, d)
        s = per_product_series(df, "INTARIAN_PEPPER_ROOT")
        stats = drift_characterize(s["mid_price"])
        stats["round"] = f"R{r}"
        stats["day"] = d
        rows.append(stats)
    return rows


def print_drift(rows: list[dict]) -> str:
    buf = []
    buf.append("| Round | Day | Ticks | NetDrift | Up% | Down% | Flat% | DirFlips | MaxDrawup | MaxDrawdown |")
    buf.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        buf.append(
            f"| {r['round']} | {r['day']} | {r['ticks']} | {r['net_drift']:+,.0f} | "
            f"{r['frac_up']:.1f} | {r['frac_dn']:.1f} | {r['frac_flat']:.1f} | "
            f"{r['dir_flips']} | {r['max_drawup']:+.1f} | {r['max_drawdown']:+.1f} |"
        )
    return "\n".join(buf)


# ---------- Task 3: EMA signal replay ----------

def ema_replay(mids: pd.Series, alpha: float = EMA_ALPHA, threshold: float = DRIFT_THRESHOLD) -> dict:
    """Replay the strategy's EMA overlay exactly as algo/strategies/pepper_root.py does.

    Seeded lazily on first tick (matches the live code: self._ema_fair = None
    until the first valid tick). Signal = fair - ema_fair.
    """
    m = mids.astype(float).reset_index(drop=True)
    ema = None
    signals: list[float] = []
    for v in m:
        if ema is None:
            ema = v
            signals.append(0.0)
            continue
        ema = alpha * v + (1 - alpha) * ema
        signals.append(v - ema)

    ser = pd.Series(signals)
    n = len(ser)
    above = ser[ser.abs() > threshold]
    n_above = len(above)
    pos = (above > 0).sum()
    neg = (above < 0).sum()

    # Sign of the triggered-bias direction per tick: +1 above+threshold,
    # -1 below -threshold, 0 otherwise. Duration = runs of same non-zero sign.
    bias = ser.apply(lambda x: 1 if x > threshold else (-1 if x < -threshold else 0))
    runs: list[tuple[int, int]] = []  # (sign, length)
    cur_sign = 0
    cur_len = 0
    for s in bias:
        if s == cur_sign:
            cur_len += 1
        else:
            if cur_sign != 0:
                runs.append((cur_sign, cur_len))
            cur_sign = s
            cur_len = 1
    if cur_sign != 0:
        runs.append((cur_sign, cur_len))
    avg_dur = (sum(length for _, length in runs) / len(runs)) if runs else 0.0

    # Count bias sign flips between +1 <-> -1 (ignoring zero runs in between).
    last_nonzero = 0
    sign_flips = 0
    for s, _ in runs:
        if last_nonzero != 0 and s != last_nonzero:
            sign_flips += 1
        last_nonzero = s

    return {
        "ticks": n,
        "threshold_hit_pct": round(100 * n_above / n, 1),
        "pos_pct": round(100 * pos / n_above, 1) if n_above else 0.0,
        "neg_pct": round(100 * neg / n_above, 1) if n_above else 0.0,
        "avg_duration": round(avg_dur, 1),
        "sign_flips": sign_flips,
        "n_runs": len(runs),
    }


def run_ema() -> list[dict]:
    targets = [
        (1, -2), (1, -1), (1, 0),
        (2, -1), (2, 0), (2, 1),
    ]
    rows = []
    for r, d in targets:
        df = load_day(r, d)
        s = per_product_series(df, "INTARIAN_PEPPER_ROOT")
        stats = ema_replay(s["mid_price"])
        stats["round"] = f"R{r}"
        stats["day"] = d
        rows.append(stats)
    return rows


def print_ema(rows: list[dict]) -> str:
    buf = []
    buf.append("| Round | Day | Ticks | Threshold_hit% | Pos% | Neg% | AvgDuration | SignFlips | Runs |")
    buf.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        buf.append(
            f"| {r['round']} | {r['day']} | {r['ticks']} | {r['threshold_hit_pct']:.1f} | "
            f"{r['pos_pct']:.1f} | {r['neg_pct']:.1f} | {r['avg_duration']:.1f} | "
            f"{r['sign_flips']} | {r['n_runs']} |"
        )
    return "\n".join(buf)


# ---------- Task 4: per-trade PnL decomposition ----------

# Merged-mode day boundaries (each day = 1,000,000 ticks in merged backtest).
DAY_BOUND = 1_000_000
# Maps (round, actual_day) -> (ts_lo, ts_hi) for the merged log.
def day_window(round_num: int, day: int) -> tuple[int, int]:
    days = R1_DAYS if round_num == 1 else R2_DAYS
    idx = days.index(day)
    return (idx * DAY_BOUND, (idx + 1) * DAY_BOUND)


def decompose_day(log: Path, round_num: int, day: int, product: str) -> dict:
    own = extract_own_trades(log, product)
    pos_rows = extract_positions_and_books(log, product)
    lo, hi = day_window(round_num, day)
    day_fills = [t for t in own if lo <= t["timestamp"] < hi]
    day_books = [r for r in pos_rows if lo <= r["timestamp"] < hi]

    # End-of-day mid (best_bid+best_ask)/2 from last book snapshot in window.
    if not day_books:
        end_mid = 0.0
    else:
        last = day_books[-1]
        bb, ba = last["best_bid"], last["best_ask"]
        end_mid = ((bb or 0) + (ba or 0)) / 2 if (bb and ba) else (bb or ba or 0)

    s = fill_summary(day_fills, end_mid)
    s["end_mid"] = end_mid
    s["round"] = f"R{round_num}"
    s["day"] = day
    return s


def run_decompose() -> list[dict]:
    targets = [
        (R1_LOG, 1, -1, "INTARIAN_PEPPER_ROOT"),  # R1 winning day
        (R2_LOG, 2, 0, "INTARIAN_PEPPER_ROOT"),   # R2 worst day
        (R2_LOG, 2, 1, "INTARIAN_PEPPER_ROOT"),   # R2 other losing day
        (R2_LOG, 2, -1, "INTARIAN_PEPPER_ROOT"),  # R2 positive day (for contrast)
    ]
    return [decompose_day(log, r, d, p) for log, r, d, p in targets]


def print_decompose(rows: list[dict]) -> str:
    buf = []
    buf.append("| Round | Day | Buys | Sells | BuyVol | SellVol | VWAP_buy | VWAP_sell | VWAP_spread | Realized | EndPos | InvPnL | Total | EndMid |")
    buf.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        buf.append(
            f"| {r['round']} | {r['day']} | {r['n_buys']} | {r['n_sells']} | "
            f"{r['buy_vol']} | {r['sell_vol']} | "
            f"{r['vwap_buy']:.1f} | {r['vwap_sell']:.1f} | {r['vwap_spread']:+.2f} | "
            f"{r['realized_pnl']:+,.0f} | {r['end_pos']:+d} | "
            f"{r['inventory_pnl']:+,.0f} | {r['total_pnl']:+,.0f} | {r['end_mid']:.1f} |"
        )
    return "\n".join(buf)


# ---------- Entry ----------

def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("baseline", "all"):
        print("## Task 1 - Baseline comparison\n")
        print(print_baseline(run_baseline()))
        print()
    if cmd in ("drift", "all"):
        print("## Task 2 - Intra-day drift (Pepper, rolling window=500)\n")
        print(print_drift(run_drift()))
        print()
    if cmd in ("ema", "all"):
        print(f"## Task 3 - EMA signal replay (alpha={EMA_ALPHA}, threshold={DRIFT_THRESHOLD})\n")
        print(print_ema(run_ema()))
        print()
    if cmd in ("decompose", "all"):
        print("## Task 4 - Per-trade PnL decomposition (Pepper)\n")
        print(print_decompose(run_decompose()))
        print()


if __name__ == "__main__":
    main()
