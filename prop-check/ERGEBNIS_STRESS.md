# Stress test result (19.10.2026, real Dukascopy EURUSD ticks)

| Rule | Correct |
|---|---|
| Baseline (holding time) | 6 / 9 |
| v1 trade-level flip check | 8 / 9 – missed K9 (quiet 0.3 pip exploiter); did NOT false-flag K8 on real ticks (only 1 flipped trade, below 3) |
| v2 account-level advantage test | **9 / 9** – pre-registered target (≥ 8 / 9) met |

Honest caveats:
- K9 is easy for v2: its advantage is exactly 0.3 pip on every trade (zero variance, huge t-value). A real quiet exploiter would vary; that case is not tested yet.
- K8 had a mean advantage of 0.099 pip – just under the 0.1 pip threshold – but a t-value of only 0.9, so the t-test, not the mean, cleared it.
- v2 needs ≥ 20 trades: K3 and K6 (15 trades) are only covered by v1.
- v2 was written after v1 failed on synthetic ticks; this real-tick run was its first contact with real data.
- All accounts are simulated from real ticks, not real prop-firm accounts.
