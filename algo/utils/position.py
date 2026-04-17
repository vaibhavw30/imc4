"""Position-aware order sizing helpers."""


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
