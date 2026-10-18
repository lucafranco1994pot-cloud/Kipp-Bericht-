# Kipp-Bericht – does price-data repair flip trading decisions?

Pre-registered experiment. Code and parameters are frozen in this commit **before** the first market-data run. Nothing will be changed after seeing results.

## Fixed setup
- Rule: SMA20 crosses SMA50 on daily `Close` (not `Adj Close`). Up = BUY, down = SELL, else NO ACTION.
- Period: 2020-01-01 to 2024-12-31.
- 30 stocks: 10 US, 10 Hong Kong, 10 London (see `kipp_beweis.py`).
- Each stock is downloaded twice with yfinance: `repair=False` and `repair=True`.

## What it reports
- Every day where the decision differs between the two data versions.
- Cause check: each changed close price in the 51-price window is reverted one at a time. The first single reversion that restores the original decision is reported; otherwise "several changes act together".
- Missing days or invalid prices block the comparison. Nothing is filled in.

## Test quality
- 10 synthetic logic tests: 10/10 pass (`testergebnisse/`).
- 6 deliberately broken program versions: all 6 are caught by the tests (`mutanten_test.py`, `mutanten_ergebnis.csv`).

## Limits
This compares raw vs. repaired yfinance responses. It is **not** proof of a later vendor correction or of a real executed trade. yfinance repairs can themselves be wrong. Zero flips is a valid result.

## Run it
Open `Kipp_Bericht_Colab.ipynb` in Google Colab and run the cells in order. See `START_HIER.txt` (German).
