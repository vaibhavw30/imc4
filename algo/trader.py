"""Main entry point for IMC Prosperity 4 — Round 1.

============================================================================
SUBMISSION NOTE — READ BEFORE UPLOADING
============================================================================
IMC's submission UI accepts a single Python file. The package layout below
(algo/strategies/*, algo/utils/*, algo/logger.py) is for local development
with prosperity4btest, not for direct upload.

Before submitting, flatten this file: paste the contents of algo/logger.py,
algo/utils/order_book.py, algo/utils/position.py, algo/strategies/base.py,
algo/strategies/osmium.py, and algo/strategies/pepper_root.py into a single
trader.py, drop the `from algo.* import ...` lines, and verify with one
local backtest before submitting. (TODO: add scripts/flatten.py to automate.)
============================================================================
"""

from datamodel import Order, Symbol, TradingState

from algo.logger import Logger
from algo.strategies.osmium import OsmiumStrategy
from algo.strategies.pepper_root import PepperRootStrategy

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
        trader_data = ""  # no per-tick state persisted yet

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
