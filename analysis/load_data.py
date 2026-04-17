"""CSV loading utilities for IMC Prosperity round data.

CSV format: semicolon-separated. Prices files have one row per
(timestamp, product) with up to three depth levels per side.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

EXPECTED_PRICE_COLUMNS = {
    "day", "timestamp", "product",
    "bid_price_1", "bid_volume_1", "bid_price_2", "bid_volume_2", "bid_price_3", "bid_volume_3",
    "ask_price_1", "ask_volume_1", "ask_price_2", "ask_volume_2", "ask_price_3", "ask_volume_3",
    "mid_price", "profit_and_loss",
}


def load_prices(round_num: int, day: int, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load prices_round_<round_num>_day_<day>.csv. Raises if missing/malformed."""
    path = data_dir / f"prices_round_{round_num}_day_{day}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Prices file not found: {path}")
    df = pd.read_csv(path, sep=";")
    missing = EXPECTED_PRICE_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path}: missing expected columns {sorted(missing)}")
    return df


def load_trades(round_num: int, day: int, data_dir: Path = DATA_DIR) -> pd.DataFrame | None:
    """Load trades_round_<round_num>_day_<day>.csv if present, else None."""
    path = data_dir / f"trades_round_{round_num}_day_{day}.csv"
    if not path.exists():
        return None
    return pd.read_csv(path, sep=";")


def load_all_days(
    round_num: int,
    days: tuple[int, ...] = (-2, -1, 0),
    data_dir: Path = DATA_DIR,
) -> dict[int, pd.DataFrame]:
    """Load every available day for a round into {day: DataFrame}."""
    out: dict[int, pd.DataFrame] = {}
    for day in days:
        try:
            out[day] = load_prices(round_num, day, data_dir)
        except FileNotFoundError:
            continue
    if not out:
        raise FileNotFoundError(
            f"No prices_round_{round_num}_day_*.csv files found in {data_dir}"
        )
    return out


def split_by_product(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return one DataFrame per product, sorted by (day, timestamp)."""
    return {
        product: subset.sort_values(["day", "timestamp"]).reset_index(drop=True)
        for product, subset in df.groupby("product")
    }
