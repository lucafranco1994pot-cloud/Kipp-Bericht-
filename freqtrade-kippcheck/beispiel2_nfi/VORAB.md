# Kipp-Check Beispiel 2 – NostalgiaForInfinity X8 – vorab festgelegt (18.10.2026)

Why this strategy: NostalgiaForInfinity is one of the best-known community strategies for Freqtrade (iterativv/NostalgiaForInfinity, GPL-3.0). File copied unchanged: `strategies/NostalgiaForInfinityX8.py` (v18.0.142).

Fixed before the first run:
- Data: OKX spot, 5m (+15m/1h/4h/1d informative), full year 2025
- Pairs: BTC, ETH, SOL, XRP, ADA, DOGE, LINK, AVAX, DOT, LTC (all /USDT; all in NFI's own OKX backtest list)
- Config close to NFI's example config: 1000 USDT, max 6 open trades, stake "unlimited", grinding on, limit orders (`config.json`)
- A original: fee 0.1 % per side
- B double fee: 0.2 % per side
- C one candle delay: entry/exit SIGNALS one candle later (`strategies/kipp_verzoegerung_nfi.py`); NFI's own custom exit logic unchanged
- Comparison trade by trade (`../vergleich.py`). A vs B: same pair + same entry time. A vs C: original entry + 5 minutes (lesson from example 1, fixed here before the run)

Nothing is changed after seeing results. No return promise, no investment advice.
