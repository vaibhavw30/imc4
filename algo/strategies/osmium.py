"""Market-making strategy for ASH_COATED_OSMIUM (stable / fixed-fair-value).

Modeled on Prosperity 3's RAINFOREST_RESIN: the price oscillates tightly
around a single integer fair value. Strategy:
  1. TAKE: lift any ask priced strictly below fair_value, hit any bid
     strictly above. This captures the obvious mispricings.
  2. MAKE: post passive quotes at fair_value ± make_edge, sized to lean
     against current inventory (skew toward flat).
"""

from datamodel import Order, TradingState

from algo.strategies.base import Strategy
from algo.utils.order_book import best_ask, best_bid
from algo.utils.position import clamp_order_size

# TODO calibrate from data: run `python -m analysis.explore` and read the
# "mode (rounded int)" line for ASH_COATED_OSMIUM in the printed stats.
# 10000 is the placeholder borrowed from sample.py's anchor.
OSMIUM_FAIR_VALUE = 10_000

# Confirmed from sample.py in nabayansaha/imc-prosperity-4-backtester.
# Prosperity 4 raised limits vs P3 (which used 50). Re-verify this against
# the official Round 1 problem statement before submission.
OSMIUM_POSITION_LIMIT = 80

# Passive quote distance from fair value (in ticks). Stable products
# tolerate tight quotes since the price barely moves.
OSMIUM_MAKE_EDGE = 1

# Default size for each passive quote; gets skewed by inventory.
OSMIUM_BASE_QUOTE_SIZE = 20


class OsmiumStrategy(Strategy):
    def __init__(
        self,
        symbol: str = "ASH_COATED_OSMIUM",
        position_limit: int = OSMIUM_POSITION_LIMIT,
        fair_value: int = OSMIUM_FAIR_VALUE,
        make_edge: int = OSMIUM_MAKE_EDGE,
        base_size: int = OSMIUM_BASE_QUOTE_SIZE,
    ):
        super().__init__(symbol, position_limit)
        self.fair_value = fair_value
        self.make_edge = make_edge
        self.base_size = base_size

    def run(self, state: TradingState) -> list[Order]:
        if self.symbol not in state.order_depths:
            return []
        order_depth = state.order_depths[self.symbol]
        position = state.position.get(self.symbol, 0)
        orders: list[Order] = []

        # ---- Phase 1: TAKE obvious mispricings ----
        # Walk the ask side from best (lowest) inward; lift anything strictly
        # below fair. Update post_take_pos as we go so the next clamp uses
        # the simulated post-take position.
        post_take_pos = position
        for ask_price in sorted(order_depth.sell_orders):
            if ask_price >= self.fair_value:
                break
            available = -order_depth.sell_orders[ask_price]  # sell_orders are negative
            qty = clamp_order_size(post_take_pos, available, self.position_limit)
            if qty > 0:
                orders.append(Order(self.symbol, ask_price, qty))
                post_take_pos += qty

        # Walk the bid side from best (highest) inward; hit anything strictly above.
        for bid_price in sorted(order_depth.buy_orders, reverse=True):
            if bid_price <= self.fair_value:
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
