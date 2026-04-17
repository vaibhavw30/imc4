"""Extract per-product per-day PnL, fills, positions, and book features from backtester logs.

Run from repo root (uses PYTHONPATH=.)

The prosperity4btest log has 3 sections:
  1. "Sandbox logs:" - per-tick JSON with compressed TradingState
  2. "Activities log:" - CSV with mid_price, profit_and_loss
  3. "Trade History:" - JSON array of all trades (ours + bots)

This script parses sections 1 and 3 for diagnostic analysis.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def split_sections(path: Path) -> tuple[str, str, str]:
    raw = path.read_text()
    m_sbx = raw.index("Sandbox logs:")
    m_act = raw.index("Activities log:")
    m_trd = raw.index("Trade History:")
    sandbox = raw[m_sbx + len("Sandbox logs:") : m_act]
    activities = raw[m_act + len("Activities log:") : m_trd]
    trades = raw[m_trd + len("Trade History:") :]
    return sandbox, activities, trades


def parse_activities_final_pnl(activities_csv: str) -> dict[tuple[int, str], float]:
    """Returns {(day, product): final_pnl} from the Activities CSV.

    The CSV is ';'-delimited with columns including day, timestamp, product,
    profit_and_loss. Final PnL per (day, product) is the last non-null row.
    """
    reader = csv.DictReader(io.StringIO(activities_csv.strip()), delimiter=";")
    last: dict[tuple[int, str], float] = {}
    for row in reader:
        day = int(row["day"])
        product = row["product"]
        pnl = row.get("profit_and_loss", "").strip()
        if pnl == "":
            continue
        try:
            last[(day, product)] = float(pnl)
        except ValueError:
            continue
    return last


def parse_trade_history(trades_json: str) -> list[dict]:
    """Parse the Trade History JSON, cleaning trailing commas."""
    raw = trades_json.strip()
    cleaned = re.sub(r",(\s*[}\]])", r"\1", raw)
    return json.loads(cleaned)


def iter_sandbox_ticks(sandbox_text: str):
    """Yield (timestamp, lambda_payload_list) per tick.

    The sandbox text is a stream of JSON objects separated by whitespace. Each
    has a lambdaLog string which itself is a JSON-encoded list with 5 elements:
    [compressed_state, compressed_orders, conversions, trader_data, logs].
    compressed_state = [ts, trader_data, listings, order_depths, own_trades,
                        market_trades, position, observations]
    """
    decoder = json.JSONDecoder()
    idx = 0
    text = sandbox_text
    n = len(text)
    while idx < n:
        while idx < n and text[idx] in " \t\r\n":
            idx += 1
        if idx >= n:
            break
        obj, end = decoder.raw_decode(text, idx)
        idx = end
        ts = obj.get("timestamp", 0)
        lam = obj.get("lambdaLog", "")
        if not lam:
            continue
        payload = json.loads(lam)
        yield ts, payload


def extract_positions_and_books(log_path: Path, product: str) -> list[dict]:
    """For a single product, return per-tick rows with timestamp, position,
    best_bid, best_ask, spread, bid_depth_best, ask_depth_best, total_bid_depth,
    total_ask_depth.
    """
    sandbox, _, _ = split_sections(log_path)
    rows = []
    for ts, payload in iter_sandbox_ticks(sandbox):
        compressed_state = payload[0]
        # [ts, trader_data, listings, order_depths, own_trades, market_trades, position, observations]
        order_depths = compressed_state[3]
        position_dict = compressed_state[6]
        pos = position_dict.get(product, 0)
        depth = order_depths.get(product)
        if not depth:
            continue
        buy_orders = {int(p): v for p, v in depth[0].items()} if depth[0] else {}
        sell_orders = {int(p): v for p, v in depth[1].items()} if depth[1] else {}
        best_bid = max(buy_orders) if buy_orders else None
        best_ask = min(sell_orders) if sell_orders else None
        bid_depth_best = buy_orders.get(best_bid, 0) if best_bid is not None else 0
        ask_depth_best = -sell_orders.get(best_ask, 0) if best_ask is not None else 0
        total_bid_depth = sum(buy_orders.values())
        total_ask_depth = -sum(sell_orders.values())
        spread = (best_ask - best_bid) if (best_bid and best_ask) else None
        rows.append({
            "timestamp": ts,
            "position": pos,
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "bid_depth_best": bid_depth_best,
            "ask_depth_best": ask_depth_best,
            "total_bid_depth": total_bid_depth,
            "total_ask_depth": total_ask_depth,
        })
    return rows


def extract_own_trades(log_path: Path, product: str) -> list[dict]:
    """Parse Trade History, return only OUR trades for `product`.

    A trade is ours if buyer='SUBMISSION' (we bought) or seller='SUBMISSION'
    (we sold). Returns list of dicts with side ('buy'/'sell'), price, quantity,
    timestamp.
    """
    _, _, trades_raw = split_sections(log_path)
    trades = parse_trade_history(trades_raw)
    own = []
    for t in trades:
        if t.get("symbol") != product:
            continue
        buyer = t.get("buyer", "")
        seller = t.get("seller", "")
        if buyer == "SUBMISSION":
            own.append({"side": "buy", "price": t["price"], "quantity": t["quantity"], "timestamp": t["timestamp"]})
        elif seller == "SUBMISSION":
            own.append({"side": "sell", "price": t["price"], "quantity": t["quantity"], "timestamp": t["timestamp"]})
    return own


def fill_summary(own_trades: list[dict], end_of_day_mid: float) -> dict:
    """Compute VWAP, counts, realized PnL, inventory PnL."""
    buys = [t for t in own_trades if t["side"] == "buy"]
    sells = [t for t in own_trades if t["side"] == "sell"]
    buy_vol = sum(t["quantity"] for t in buys)
    sell_vol = sum(t["quantity"] for t in sells)
    buy_notional = sum(t["price"] * t["quantity"] for t in buys)
    sell_notional = sum(t["price"] * t["quantity"] for t in sells)
    vwap_buy = (buy_notional / buy_vol) if buy_vol else float("nan")
    vwap_sell = (sell_notional / sell_vol) if sell_vol else float("nan")
    matched = min(buy_vol, sell_vol)
    realized = (vwap_sell - vwap_buy) * matched if matched else 0.0
    end_pos = buy_vol - sell_vol
    inventory_pnl = end_pos * end_of_day_mid - (buy_notional if end_pos > 0 else sell_notional if end_pos < 0 else 0)
    # cleaner: mark-to-market the net position at end-of-day mid
    inventory_pnl = end_pos * end_of_day_mid - (end_pos * vwap_buy if end_pos > 0 else end_pos * vwap_sell if end_pos < 0 else 0)
    return {
        "n_buys": len(buys),
        "n_sells": len(sells),
        "buy_vol": buy_vol,
        "sell_vol": sell_vol,
        "vwap_buy": vwap_buy,
        "vwap_sell": vwap_sell,
        "vwap_spread": (vwap_sell - vwap_buy) if (buy_vol and sell_vol) else float("nan"),
        "realized_pnl": realized,
        "end_pos": end_pos,
        "inventory_pnl": inventory_pnl,
        "total_pnl": realized + inventory_pnl,
    }


def position_trajectory_summary(pos_rows: list[dict], limit: int = 80) -> dict:
    positions = [r["position"] for r in pos_rows]
    if not positions:
        return {}
    n = len(positions)
    abs_pos = [abs(p) for p in positions]
    zero_crossings = 0
    for i in range(1, n):
        a, b = positions[i - 1], positions[i]
        if (a > 0 and b < 0) or (a < 0 and b > 0) or (a != 0 and b == 0) or (a == 0 and b != 0):
            zero_crossings += 1
    mean_pos = sum(positions) / n
    mean_abs = sum(abs_pos) / n
    var = sum((p - mean_pos) ** 2 for p in positions) / n
    std = var**0.5
    pct_over_40 = sum(1 for p in abs_pos if p > 40) / n
    pct_pinned = sum(1 for p in abs_pos if p == limit) / n
    return {
        "ticks": n,
        "mean_pos": mean_pos,
        "mean_abs_pos": mean_abs,
        "std_pos": std,
        "zero_crossings": zero_crossings,
        "pct_over_40": pct_over_40,
        "pct_pinned": pct_pinned,
        "max_abs": max(abs_pos),
    }


def book_feature_summary(pos_rows: list[dict]) -> dict:
    n = len(pos_rows)
    if n == 0:
        return {}
    spreads = [r["spread"] for r in pos_rows if r["spread"] is not None]
    mean_spread = sum(spreads) / len(spreads) if spreads else float("nan")
    deep_best = sum(1 for r in pos_rows if r["bid_depth_best"] > 20 or r["ask_depth_best"] > 20) / n
    asymmetric = sum(
        1 for r in pos_rows
        if abs(r["bid_depth_best"] - r["ask_depth_best"]) > 10
    ) / n
    mean_bid_depth = sum(r["bid_depth_best"] for r in pos_rows) / n
    mean_ask_depth = sum(r["ask_depth_best"] for r in pos_rows) / n
    mean_total_bid = sum(r["total_bid_depth"] for r in pos_rows) / n
    mean_total_ask = sum(r["total_ask_depth"] for r in pos_rows) / n
    return {
        "ticks": n,
        "mean_spread": mean_spread,
        "pct_deep_best": deep_best,
        "pct_asymmetric": asymmetric,
        "mean_bid_depth_best": mean_bid_depth,
        "mean_ask_depth_best": mean_ask_depth,
        "mean_total_bid_depth": mean_total_bid,
        "mean_total_ask_depth": mean_total_ask,
    }


def main():
    if len(sys.argv) < 2:
        print("usage: parse_log.py <command> [args...]")
        print("commands: pnl <logfile> | fills <logfile> <product> | positions <logfile> <product> | books <logfile> <product>")
        sys.exit(1)
    cmd = sys.argv[1]
    path = Path(sys.argv[2])
    if cmd == "pnl":
        pnls = parse_activities_final_pnl(split_sections(path)[1])
        for k in sorted(pnls):
            print(f"day={k[0]}  product={k[1]:24s}  pnl={pnls[k]:12,.2f}")
        return
    product = sys.argv[3]
    if cmd == "fills":
        own = extract_own_trades(path, product)
        # Need end-of-day mid from activities
        pnls = parse_activities_final_pnl(split_sections(path)[1])
        pos_rows = extract_positions_and_books(path, product)
        end_mid = ((pos_rows[-1]["best_bid"] or 0) + (pos_rows[-1]["best_ask"] or 0)) / 2 if pos_rows else 0
        s = fill_summary(own, end_mid)
        for k, v in s.items():
            if isinstance(v, float):
                print(f"  {k:20s}: {v:12,.3f}")
            else:
                print(f"  {k:20s}: {v}")
    elif cmd == "positions":
        pos_rows = extract_positions_and_books(path, product)
        s = position_trajectory_summary(pos_rows)
        for k, v in s.items():
            if isinstance(v, float):
                print(f"  {k:20s}: {v:12,.3f}")
            else:
                print(f"  {k:20s}: {v}")
    elif cmd == "books":
        pos_rows = extract_positions_and_books(path, product)
        s = book_feature_summary(pos_rows)
        for k, v in s.items():
            if isinstance(v, float):
                print(f"  {k:20s}: {v:12,.3f}")
            else:
                print(f"  {k:20s}: {v}")
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
