# Kipp-Check Beispiel 2 – NostalgiaForInfinity X8 – Ergebnis (18.10.2026)

Pre-registered in `VORAB.md`, run unchanged. Raw output: `ergebnisse/lauf_20261018T173644Z`.

| Run | Trades | Profit 2025 |
|---|---|---|
| A original (fee 0.1 %) | 60 | +296.3 USDT (+29.6 %) |
| B double fee (0.2 %) | 59 | +307.5 USDT (+30.7 %) |
| C signals one candle later | 53 | +188.9 USDT (+18.9 %) |

**C – one candle delay:** 50 of 60 trades (83 %) flip: 9 disappear, 2 new, 39 exit differently. **More than a third of the profit is gone** (-107 USDT). The result depends strongly on reacting within the same 5-minute candle – something live trading (latency, order fills) does not guarantee.

**B – double fee:** 24 of 60 trades (40 %) flip, mostly different exits; 1 trade disappears. Surprisingly the profit is slightly *higher*. Higher fees push exit targets and change exit timing – and here that happened to help. A result that moves up when costs go up is a sign that the exact numbers depend on exit-timing details, not only on the edge.

Limits: only 60 trades (small sample), one year, 10 large coins on OKX spot, backtest only, no live trading. Not investment advice.
