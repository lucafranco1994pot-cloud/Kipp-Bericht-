# Execution check for prop firms – demo, pre-registered (18.10.2026)

Question: can a trade-level check separate accounts that profit from stale prices ("latency arbitrage") from honest fast traders – better than a simple holding-time rule?

Method (one change per trade): replace the logged entry price by the real market price at the same moment (independent Dukascopy EURUSD ticks). A trade "flips" if it was profitable as logged, is not profitable at the real market price, and the logged price was better than the market by more than 0.5 pip (tolerance for feed differences). An account is flagged with 3 or more flipped trades.

Baseline (typical rule): flag if median holding time < 60 s or at least half of the trades are held < 30 s.

Data: Dukascopy EURUSD ticks, 3–7 March 2025, 07–18 UTC. Seven test accounts with a known truth (`latenz_check.py`):
K1 stale-price exploiter (5 s) – EXPLOITER · K2 scalper, real fills – CLEAN · K3 swing, real fills – CLEAN · K4 swing + every 10th exploit trade hidden – EXPLOITER · K5 fast news trader, real fills – CLEAN · K6 swing with ±0.3 pip slippage noise – CLEAN · K7 exploiter holding 10 min (disguised) – EXPLOITER

Success criterion fixed now: the flip check is right on at least 6 of 7 accounts and on more accounts than the baseline. The logic was tested once on synthetic ticks before this freeze (7/7, baseline 4/7); the real-tick run comes after this commit and is reported whatever it shows.

Limits: demo accounts are simulated from real ticks, not real prop-firm accounts; a prop firm's own price feed differs from Dukascopy.
