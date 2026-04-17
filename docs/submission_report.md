# Round 1 Submission Report

**Date:** 2026-04-17
**File to upload:** `dist/bigballers.py` (18,179 bytes, 471 lines)
**Generated from:** modular source at `algo/*` via `scripts/flatten.py`
**Strategy:** unchanged from Sprint 1 — shipping v1 as diagnosed

---

## 1. Backtest numbers to expect

### Combined 3-day backtest

| Matcher | Total PnL | Sharpe | Max DD |
|---|---:|---:|---:|
| `--match-trades all` (default) | **101,414** | 1.343 | 2.68% |
| `--match-trades worse` | **117,616** | 1.835 | 2.68% |

Flat `dist/bigballers.py` matches modular `algo/trader.py` **to the cent** under both matchers.

### Per-product per-day breakdown (match-trades all)

| Day | ASH_COATED_OSMIUM | INTARIAN_PEPPER_ROOT | Total |
|---|---:|---:|---:|
| Day −2 | 13,183 | 4,298 | 17,482 |
| Day −1 | 15,569 | 47,228 | 62,797 |
| Day 0 | 13,850 | 7,286 | 21,136 |
| **Total** | **42,602** | **58,812** | **101,414** |

### Per-product per-day breakdown (match-trades worse)

| Day | ASH_COATED_OSMIUM | INTARIAN_PEPPER_ROOT | Total |
|---|---:|---:|---:|
| Day −2 | 12,739 | 14,186 | 26,926 |
| Day −1 | 15,420 | 48,452 | 63,872 |
| Day 0 | 13,400 | 13,418 | 26,818 |
| **Total** | **41,559** | **76,056** | **117,616** |

---

## 2. Expected live PnL range

From `docs/diagnostic_round_2.md` (numbers after a 50% haircut for live-vs-practice degradation):

- **Osmium per day:** 12.7–15.4k → live 6–15k/day → **3-day: 20–45k**
- **Pepper MM edge per day:** stable ~23–26k when clean, can flip to −19k when whipsawed → **3-day: −30k to +50k**
- **Pepper inventory drift:** essentially random walk → **3-day: −30k to +30k**

**Expected range: 15k – 85k over 3 days. Most likely outcome 40–60k. Hard floor ≈ 20k** (Osmium alone after haircut; Pepper degenerate).

---

## 3. Upload instructions

1. File location: `/Users/vaibhav.wudaru/imc4/dist/bigballers.py`.
2. Submit via IMC's Round 1 upload form — single-file, no external dependencies beyond `datamodel` (which IMC provides).
3. After IMC runs its internal backtest, compare against the numbers in §1. They may not match exactly (IMC's matcher could differ from `prosperity4btest`), but they should be the same order of magnitude.

To regenerate the flat file from source after any strategy change:
```
python3 scripts/flatten.py
```

---

## 4. What to watch on IMC's in-app backtest

- **Non-zero PnL per product.** If either product is at 0, something broke at import time.
- **Order of magnitude.** Expect total PnL in the 20k–150k range. <10k or >500k → investigate.
- **No exceptions in platform logs.** The `Trader.run` method wraps each strategy in try/except, so one product crashing won't kill the other — but exceptions would show in the logs and degrade PnL.
- **Position should move.** Osmium position oscillates near 0 (mean abs ~5–10, max 80). Pepper position depends on the day (mean +3 to +39 in practice).

---

## 5. Known risks

1. **Pepper PnL is volatile day-to-day.** Practice range: 4k–48k per day. On live, a day with the same MM rate but an unlucky inventory × drift pairing could easily produce 0 or slightly negative Pepper PnL.
2. **Pepper directional inventory swing.** Day −1's 47k came partly from accumulating +43 inventory against an upward drift. Live expectation for this component is 0 ± 30k over 3 days.
3. **Osmium is the reliable floor.** 12.7–15.4k/day with std 1.35k/day (Sharpe 9.92). If Pepper turns to noise, Osmium alone gives ~41k backtest → ~20k post-haircut.
4. **Matcher sensitivity is mild and favorable.** `worse` matcher gives *more* PnL than `all`, so IMC's (unknown) live matcher is unlikely to degrade us catastrophically on the MM edge.

---

## 6. Pre-submission checklist — all passed

- Imports: only `json`, `abc.{ABC,abstractmethod}`, `typing.Any`, and `datamodel.*`. No `algo.*` or relative imports.
- `OSMIUM_FAIR_VALUE = 10_000` present.
- Position limits = 80 for both products.
- `Logger` class unmodified from jmerle format.
- `Trader.run(self, state)` returns `(orders_dict, conversions, trader_data)`.
- Only `print(` call is inside `Logger.flush` (required for the sentinel-prefixed stdout JSON).
- `ast.parse` succeeds.
- Exactly one of each: `Logger`, `Strategy`, `OsmiumStrategy`, `PepperRootStrategy`, `Trader`.
- Strategies wrapped in `try/except` inside `Trader.run`.
- PnL: flat = modular to the cent under both matchers.
