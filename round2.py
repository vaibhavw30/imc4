"""IMC Prosperity 4 - Round 2 submission (flat single-file build).

Generated from the modular source at algo/* by scripts/flatten.py.
DO NOT EDIT DIRECTLY - edit the source files and re-run the flattener.

================================================================
 MARKET ACCESS FEE (MAF)
================================================================
 Round 2 introduces an optional Market Access Fee. Teams in the
 top 50% of MAF bids win access to an additional 25% quote volume
 (and pay their bid); the bottom 50% pay nothing and trade at
 baseline volume.

 We declare our MAF below as MARKET_ACCESS_FEE and also publish
 it every tick in trader_data under the "maf" key, so the engine
 can pick it up regardless of which field it reads.

 Sizing reasoning (see write-up):
   - Round 1 baseline PnL ≈ 140,000 XIRECS at our rank.
   - +25% volume ⇒ ~35,000 extra XIRECS in the optimistic case,
     ~28,000 in a conservative case (marginal fills at worse
     prices, position-limit saturation).
   - Break-even MAF is therefore ~28k–35k.
   - Target: bid ~15-20% of conservative extra = 4,200-5,600.
     Chosen point leaves ~4.5x upside on the fee and carries
     enough weight to beat the median of a field where ~half
     the teams bid zero or token amounts.
"""

MARKET_ACCESS_FEE: int = 5000

import json

from abc import ABC, abstractmethod
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import Any

# --- Logger (from algo/logger.py) ---

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])
        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]
        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [trade.symbol, trade.price, trade.quantity, trade.buyer, trade.seller, trade.timestamp]
                )
        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]
        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])
        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        lo, hi = 0, min(len(value), max_length)
        out = ""

        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."
            encoded_candidate = json.dumps(candidate)
            if len(encoded_candidate) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1

        return out

# --- Order book utilities (from algo/utils/order_book.py) ---

def best_bid(order_depth: OrderDepth) -> tuple[int, int] | None:
    """Highest bid as (price, volume), or None if no bids exist."""
    if not order_depth.buy_orders:
        return None
    price = max(order_depth.buy_orders)
    return price, order_depth.buy_orders[price]


def best_ask(order_depth: OrderDepth) -> tuple[int, int] | None:
    """Lowest ask as (price, volume>0), or None if no asks exist.

    Note: datamodel stores sell_orders with negative volumes; we flip
    the sign so the volume returned here is always positive.
    """
    if not order_depth.sell_orders:
        return None
    price = min(order_depth.sell_orders)
    return price, -order_depth.sell_orders[price]


def mid_price(order_depth: OrderDepth) -> float | None:
    """Midpoint of best bid and best ask. None if either side is empty."""
    bb = best_bid(order_depth)
    ba = best_ask(order_depth)
    if bb is None or ba is None:
        return None
    return (bb[0] + ba[0]) / 2.0


def wall_mid(order_depth: OrderDepth, min_volume: int = 15) -> float | None:
    """Midpoint of the deepest bid and deepest ask levels.

    Theory ("Frankfurt Hedgehogs", Prosperity 3 community insight):
        Designated market makers post fat quotes that hug fair value much
        more tightly than retail/noise orders. By picking the price level
        on each side with the largest size (above `min_volume`), we get
        a "true price" estimate that filters out adverse-selection noise
        from thin levels at the top of the book.

    Falls back to a plain mid_price if no level on either side meets the
    `min_volume` threshold.
    """
    bid_walls = [(p, v) for p, v in order_depth.buy_orders.items() if v >= min_volume]
    ask_walls = [(p, -v) for p, v in order_depth.sell_orders.items() if -v >= min_volume]

    if not bid_walls or not ask_walls:
        return mid_price(order_depth)

    bid_wall_price = max(bid_walls, key=lambda pv: pv[1])[0]
    ask_wall_price = max(ask_walls, key=lambda pv: pv[1])[0]
    return (bid_wall_price + ask_wall_price) / 2.0

# --- Position utilities (from algo/utils/position.py) ---

def clamp_order_size(current_position: int, desired_qty: int, limit: int) -> int:
    """Clip a desired signed order quantity to what the position limit allows.

    Args:
        current_position: signed current position (positive = long).
        desired_qty: signed desired quantity (positive = buy, negative = sell).
        limit: absolute position limit (always positive).

    Returns:
        Signed quantity that won't breach the limit. Sign is preserved;
        zero if there is no headroom in the requested direction.
    """
    if desired_qty > 0:
        headroom = limit - current_position
        return max(0, min(desired_qty, headroom))
    if desired_qty < 0:
        headroom = limit + current_position
        return min(0, max(desired_qty, -headroom))
    return 0


def inventory_skew(position: int, limit: int) -> float:
    """Lopsidedness in [-1, 1]. +1 = maxed long, -1 = maxed short.

    Used to skew passive quotes: when long, shrink buy size and grow
    sell size (and optionally widen the bid quote / tighten the ask).
    """
    if limit <= 0:
        return 0.0
    return max(-1.0, min(1.0, position / limit))

# --- Strategy base class (from algo/strategies/base.py) ---

class Strategy(ABC):
    """One strategy per product. Trader composes them and dispatches each tick."""

    def __init__(self, symbol: str, position_limit: int):
        self.symbol = symbol
        self.position_limit = position_limit

    @abstractmethod
    def run(self, state: TradingState) -> list[Order]:
        """Return the orders to submit for this product on this timestep.

        Implementations should be defensive — return [] rather than raise
        if the order book is empty or unusable. Trader.run() also wraps
        this call in try/except as a safety net.
        """
        ...

# --- Osmium strategy (from algo/strategies/osmium.py) ---

# OSMIUM fair value is grounded in three days of historical data:
#   - mid_price median = 10001.0 across all ~30k usable ticks
#   - mid_price mean   = 10000.88
# The Round 1 anchor of 10000 was ~1 tick low. Using 10001 improves
# edge on every take and shifts passive quotes by 1 tick; cumulative
# across thousands of fills this is a non-trivial uplift.
OSMIUM_FAIR_VALUE = 10_001

# Confirmed from sample.py in nabayansaha/imc-prosperity-4-backtester.
# Prosperity 4 raised limits vs P3 (which used 50). Re-verify this against
# the official Round 1 problem statement before submission.
OSMIUM_POSITION_LIMIT = 80

# Passive quote distance from fair value (in ticks). Stable products
# tolerate tight quotes since the price barely moves. Bumped from 1 to 2:
# historical |trade - mid| has std ~8 ticks, so ±1 quotes are sitting
# inside the noise and get adversely selected. ±2 keeps us inside the
# ~16-tick median spread but with one tick of buffer.
OSMIUM_MAKE_EDGE = 2

# Minimum edge (ticks) before TAKING on OSMIUM. A taker-side counterpart
# to OSMIUM_MAKE_EDGE: the old code took anything strictly on the correct
# side of fair, including 1-tick mispricings that are indistinguishable
# from noise. Requiring at least 1 tick of edge filters out pure noise
# fills while still capturing the bimodal retail quotes at ±10.
OSMIUM_TAKE_EDGE = 1

# Default size for each passive quote; gets skewed by inventory.
OSMIUM_BASE_QUOTE_SIZE = 20


class OsmiumStrategy(Strategy):
    def __init__(
        self,
        symbol: str = "ASH_COATED_OSMIUM",
        position_limit: int = OSMIUM_POSITION_LIMIT,
        fair_value: int = OSMIUM_FAIR_VALUE,
        make_edge: int = OSMIUM_MAKE_EDGE,
        take_edge: int = OSMIUM_TAKE_EDGE,
        base_size: int = OSMIUM_BASE_QUOTE_SIZE,
    ):
        super().__init__(symbol, position_limit)
        self.fair_value = fair_value
        self.make_edge = make_edge
        self.take_edge = take_edge
        self.base_size = base_size

    def run(self, state: TradingState) -> list[Order]:
        if self.symbol not in state.order_depths:
            return []
        order_depth = state.order_depths[self.symbol]
        position = state.position.get(self.symbol, 0)
        orders: list[Order] = []

        # ---- Phase 1: TAKE obvious mispricings ----
        # Walk the ask side from best (lowest) inward; lift anything with at
        # least `take_edge` ticks of edge below fair. Update post_take_pos
        # as we go so the next clamp uses the simulated post-take position.
        post_take_pos = position
        take_threshold_ask = self.fair_value - self.take_edge
        take_threshold_bid = self.fair_value + self.take_edge
        for ask_price in sorted(order_depth.sell_orders):
            if ask_price > take_threshold_ask:
                break
            available = -order_depth.sell_orders[ask_price]  # sell_orders are negative
            qty = clamp_order_size(post_take_pos, available, self.position_limit)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                post_take_pos += qty

        # Walk the bid side from best (highest) inward; hit anything with
        # at least `take_edge` ticks of edge above fair.
        for bid_price in sorted(order_depth.buy_orders, reverse=True):
            if bid_price < take_threshold_bid:
                break
            available = order_depth.buy_orders[bid_price]
            qty = clamp_order_size(post_take_pos, -available, self.position_limit)
            if qty < 0:
                orders.append(Order(self.symbol, bid_price, qty))
                post_take_pos += qty

        # ---- Phase 2: MAKE passive quotes ----
        bid_quote = self.fair_value - self.make_edge
        ask_quote = self.fair_value + self.make_edge

        # Inventory-skewed sizing: when long (skew > 0), shrink buy size and
        # grow sell size; vice versa when short. Using post_take_pos so we
        # don't double-count fills we just placed in phase 1.
        skew = post_take_pos / self.position_limit  # in [-1, 1]
        buy_size = max(0, int(self.base_size * (1.0 - max(0.0, skew))))
        sell_size = max(0, int(self.base_size * (1.0 + min(0.0, skew))))

        buy_size = clamp_order_size(post_take_pos, buy_size, self.position_limit)
        sell_size = clamp_order_size(post_take_pos, -sell_size, self.position_limit)

        # Don't post above the existing best bid by more than 1 tick — cap at
        # best+1 (price-time priority), and similarly on the ask side.
        bb = best_bid(order_depth)
        ba = best_ask(order_depth)
        if bb is not None and bid_quote > bb[0]:
            bid_quote = min(bid_quote, bb[0] + 1)
        if ba is not None and ask_quote < ba[0]:
            ask_quote = max(ask_quote, ba[0] - 1)

        if buy_size > 0:
            orders.append(Order(self.symbol, bid_quote, buy_size))
        if sell_size < 0:
            orders.append(Order(self.symbol, ask_quote, sell_size))

        return orders

# --- Pepper Root strategy (from algo/strategies/pepper_root.py) ---

# Confirmed from sample.py in nabayansaha/imc-prosperity-4-backtester.
# Re-verify against the official Round 1 problem statement before submission.
PEPPER_ROOT_POSITION_LIMIT = 80

# Minimum edge (ticks) between fair_value and a take/quote price before
# we'll act. Raise this if backtests show overtrading bleeds PnL.
PEPPER_MIN_EDGE = 2

# Base passive quote distance from fair_value (ticks).
PEPPER_BAND_WIDTH = 1

# Extra widening of the passive band when at the position limit
# (linearly interpolated by abs(inventory_skew)).
PEPPER_MAX_EXTRA_BAND = 2

# Default size for each passive quote.
PEPPER_BASE_QUOTE_SIZE = 12

# Volume threshold for wall_mid: a level with this much size or more is
# presumed to be a designated market maker (and thus near fair value).
# Lowered from 15 to 12: PEPPER level-2 volume has p25=17 and level-1
# p75=12, so 12 reliably catches the deeper MM level without falsely
# flagging the top-of-book retail level. Wider detection means fewer
# ticks falling back to noisy top-of-book mid.
PEPPER_WALL_VOLUME = 12

# ---- EMA drift overlay ----

# Smoothing factor for the wall_mid EMA. 0.005 ≈ ~200-tick half-life,
# slow enough to ignore tick noise, persistent enough to stay on the
# correct side of a sustained intra-day drift.
PEPPER_EMA_ALPHA = 0.005

# Minimum |wall_mid - ema| (in ticks) before the directional bias kicks
# in. Calibrated for live-scale noise (std≈29): 8 ≈ 0.28σ, so below
# this we treat the gap as noise; above it we treat it as real drift.
PEPPER_DRIFT_THRESHOLD = 8.0

# Extra quote size added on the drift-favored side (units). Deliberately
# modest so whipsaw damage is bounded relative to v1's base_size=12.
PEPPER_DRIFT_BIAS_SIZE = 8


class PepperRootStrategy(Strategy):
    def __init__(
        self,
        symbol: str = "INTARIAN_PEPPER_ROOT",
        position_limit: int = PEPPER_ROOT_POSITION_LIMIT,
        min_edge: int = PEPPER_MIN_EDGE,
        band_width: int = PEPPER_BAND_WIDTH,
        max_extra_band: int = PEPPER_MAX_EXTRA_BAND,
        base_size: int = PEPPER_BASE_QUOTE_SIZE,
        wall_volume: int = PEPPER_WALL_VOLUME,
        ema_alpha: float = PEPPER_EMA_ALPHA,
        drift_threshold: float = PEPPER_DRIFT_THRESHOLD,
        drift_bias_size: int = PEPPER_DRIFT_BIAS_SIZE,
    ):
        super().__init__(symbol, position_limit)
        self.min_edge = min_edge
        self.band_width = band_width
        self.max_extra_band = max_extra_band
        self.base_size = base_size
        self.wall_volume = wall_volume
        self.ema_alpha = ema_alpha
        self.drift_threshold = drift_threshold
        self.drift_bias_size = drift_bias_size
        # Per-day EMA state; seeded lazily on the first usable tick.
        self._ema_fair: float | None = None

    def run(self, state: TradingState) -> list[Order]:
        if self.symbol not in state.order_depths:
            return []
        order_depth = state.order_depths[self.symbol]
        position = state.position.get(self.symbol, 0)
        orders: list[Order] = []

        # Recompute fair value each tick. wall_mid filters out top-of-book
        # noise and uses the deepest level on each side; falls back to a
        # plain mid if no level meets the wall threshold.
        fair = wall_mid(order_depth, min_volume=self.wall_volume)
        if fair is None:
            fair = mid_price(order_depth)
        if fair is None:
            return []  # book is unusable this tick — sit out

        # Reset EMA at the start of each trading day. In live this is t=0;
        # in merged backtest this fires at the start of each of the 3 days.
        # Without this reset, practice backtest benefits from EMA carry-over
        # that won't exist in live (where each day is a separate submission).
        if state.timestamp == 0:
            self._ema_fair = None

        # ---- EMA update + directional signal ----
        if self._ema_fair is None:
            self._ema_fair = fair
        else:
            self._ema_fair = self.ema_alpha * fair + (1.0 - self.ema_alpha) * self._ema_fair
        signal = fair - self._ema_fair

        # ---- Phase 1: TAKE only when edge >= min_edge ----
        post_take_pos = position
        take_threshold_ask = fair - self.min_edge
        take_threshold_bid = fair + self.min_edge

        for ask_price in sorted(order_depth.sell_orders):
            if ask_price > take_threshold_ask:
                break
            available = -order_depth.sell_orders[ask_price]
            qty = clamp_order_size(post_take_pos, available, self.position_limit)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                post_take_pos += qty

        for bid_price in sorted(order_depth.buy_orders, reverse=True):
            if bid_price < take_threshold_bid:
                break
            available = order_depth.buy_orders[bid_price]
            qty = clamp_order_size(post_take_pos, -available, self.position_limit)
            if qty < 0:
                orders.append(Order(self.symbol, bid_price, qty))
                post_take_pos += qty

        # ---- Phase 2: MAKE with inventory-widened band ----
        skew_abs = abs(post_take_pos) / self.position_limit  # in [0, 1]
        edge = self.band_width + int(round(self.max_extra_band * skew_abs))

        bid_quote = int(fair - edge)
        ask_quote = int(fair + edge)

        # Don't post above the best bid; cap at best+1 (and mirror on ask).
        bb = best_bid(order_depth)
        ba = best_ask(order_depth)
        if bb is not None and bid_quote > bb[0]:
            bid_quote = bb[0] + 1
        if ba is not None and ask_quote < ba[0]:
            ask_quote = ba[0] - 1
        # If the band collapses to a cross/touch, sit out the make this tick.
        if bid_quote >= ask_quote:
            return orders

        skew = post_take_pos / self.position_limit
        buy_size = max(0, int(self.base_size * (1.0 - max(0.0, skew))))
        sell_size = max(0, int(self.base_size * (1.0 + min(0.0, skew))))

        # Directional overlay: when EMA says price is drifting, lean into
        # the drift on the passive-quote side. Dormant when |signal| is
        # below threshold, so flat markets behave exactly like v1.
        if signal > self.drift_threshold:
            buy_size += self.drift_bias_size
        elif signal < -self.drift_threshold:
            sell_size += self.drift_bias_size

        buy_size = clamp_order_size(post_take_pos, buy_size, self.position_limit)
        sell_size = clamp_order_size(post_take_pos, -sell_size, self.position_limit)

        if buy_size > 0:
            orders.append(Order(self.symbol, bid_quote, buy_size))
        if sell_size < 0:
            orders.append(Order(self.symbol, ask_quote, sell_size))

        return orders

# --- Trader (from algo/trader.py) ---

logger = Logger()


class Trader:
    def __init__(self) -> None:
        self.strategies = {
            "ASH_COATED_OSMIUM": OsmiumStrategy(),
            "INTARIAN_PEPPER_ROOT": PepperRootStrategy(),
        }

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result: dict[Symbol, list[Order]] = {}

        for symbol, strategy in self.strategies.items():
            if symbol not in state.order_depths:
                continue
            try:
                result[symbol] = strategy.run(state)
            except Exception as exc:
                # One product crashing should not take down the whole algo.
                logger.print(f"ERROR {symbol}: {type(exc).__name__}: {exc}")
                result[symbol] = []

        conversions = 0
        # Emit MAF on every tick in trader_data. The engine reads the last
        # value of this field at the end of the run; emitting every tick
        # is idempotent and makes the bid visible in logs from tick 0 on.
        trader_data = json.dumps({"maf": MARKET_ACCESS_FEE})

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data