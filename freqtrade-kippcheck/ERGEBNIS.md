# Kipp-Check Beispiel 1 – Ergebnis (18.10.2026)

Strategy: official Freqtrade SampleStrategy (unchanged), OKX spot 5m, BTC/ETH/SOL, full year 2025. Raw output: `ergebnisse/lauf_20261018T165444Z`.

| Run | Trades | Profit 2025 |
|---|---|---|
| A original (fee 0.1 %) | 550 | -251.9 USDT (-25 %) |
| B double fee (0.2 %) | 516 | -331.1 USDT (-33 %) |
| C signals one candle later | 569 | -226.0 USDT (-23 %) |

**B – double fee (pre-registered comparison):** 312 of 550 trades (57 %) flip. 41 trades disappear, 7 new ones appear, 264 keep their entry but exit at a different time. Reason: the strategy's take-profit (ROI) targets are measured after fees, so higher fees move almost every exit. 6 trades turn from take-profit into stop-loss.

**C – one candle delay:** the pre-registered matching (same pair + same entry time) is not suitable here, because every entry moves by exactly 5 minutes; it reports 1,119 "flips", which is an artefact. **Post-hoc, clearly labelled:** matching each original trade to the variant trade 5 minutes later gives 526 matched trades (519 with the same exit reason), 24 trades disappear and 43 new ones appear. The delayed version loses slightly less, which suggests the entry signal carries little edge.

Limits: one strategy, one year, one exchange; signals only from a sample strategy; no live trading. The "first flip per pair" label is weak for fee changes, because a fee change acts on every trade directly.
