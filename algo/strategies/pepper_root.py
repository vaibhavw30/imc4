"""Market-making strategy for INTARIAN_PEPPER_ROOT (drifting / random-walk).

Modeled on Prosperity 3's KELP. Key differences vs OsmiumStrategy:

  - **Fair value is recomputed every tick** from the order book using
    wall_mid. There is no fixed anchor — the price genuinely drifts —
    so any cached or hardcoded fair value goes stale within seconds.
    (sample.py uses 11_000 as a rough anchor; we keep that only as a
    sanity-check baseline, not as the live fair value.)

  - **No-trade band (min_edge).** Pepper-style products historically
    punish overtrading on tight spreads: the bot counterparty is
    informed, and crossing the spread for less than `min_edge` ticks
    of edge tends to bleed PnL. Better to sit out than quote into
    a tight book.

  - **Inventory-widening band (band_width + max_extra_band).** When
    inventory approaches the position limit, we widen the passive quote
    on the side we want to fill less aggressively, encouraging the
    opposite side to lean us back to flat.
"""

from datamodel import Order, TradingState

from algo.strategies.base import Strategy
from algo.utils.order_book import best_ask, best_bid, mid_price, wall_mid
from algo.utils.position import clamp_order_size

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
PEPPER_WALL_VOLUME = 15


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
    ):
        super().__init__(symbol, position_limit)
        self.min_edge = min_edge
        self.band_width = band_width
        self.max_extra_band = max_extra_band
        self.base_size = base_size
        self.wall_volume = wall_volume

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

        buy_size = clamp_order_size(post_take_pos, buy_size, self.position_limit)
        sell_size = clamp_order_size(post_take_pos, -sell_size, self.position_limit)

        if buy_size > 0:
            orders.append(Order(self.symbol, bid_quote, buy_size))
        if sell_size < 0:
            orders.append(Order(self.symbol, ask_quote, sell_size))

        return orders
