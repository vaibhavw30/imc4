"""Abstract base class for per-product strategies."""

from abc import ABC, abstractmethod

from datamodel import Order, TradingState


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
