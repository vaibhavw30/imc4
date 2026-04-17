"""Extract the bot baseline PnL per product per day from practice CSVs.

Run from the repo root:

    python -m analysis.baseline

The `profit_and_loss` column in prices_round_*_day_*.csv is the
reference trajectory for that book. The final non-null value per
(day, product) is the bot's end-of-day PnL — the number our strategy
needs to beat.
"""

from analysis.load_data import load_all_days, split_by_product


def main() -> None:
    per_day = load_all_days(1)

    rows: list[tuple[int, str, float]] = []
    for day, df in sorted(per_day.items()):
        by_product = split_by_product(df)
        for product, sub in by_product.items():
            pnl_series = sub["profit_and_loss"].dropna()
            if pnl_series.empty:
                continue
            final = float(pnl_series.iloc[-1])
            rows.append((day, product, final))

    print(f"{'day':>4}  {'product':<22}  {'bot_pnl':>10}")
    print("-" * 42)
    totals: dict[str, float] = {}
    for day, product, pnl in rows:
        print(f"{day:>4}  {product:<22}  {pnl:>10,.0f}")
        totals[product] = totals.get(product, 0.0) + pnl

    print("-" * 42)
    print("Per-product totals across all days:")
    grand = 0.0
    for product, total in totals.items():
        print(f"      {product:<22}  {total:>10,.0f}")
        grand += total
    print(f"{'':>28}  {'GRAND':<4}  {grand:,.0f}")


if __name__ == "__main__":
    main()
