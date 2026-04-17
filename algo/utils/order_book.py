"""Pure functions for interpreting an OrderDepth.

OrderDepth convention recap (from datamodel):
  - buy_orders: dict[price -> volume]   with positive volumes (bids)
  - sell_orders: dict[price -> volume]  with NEGATIVE volumes (asks)

Helpers in this module always return positive volumes to callers.
"""

from datamodel import OrderDepth


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
