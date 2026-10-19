# Stress test – two cases where the check could fail – pre-registered (19.10.2026)

Added accounts (`latenz_check.py --stress`, all 9 accounts are evaluated):
- K8 honest news trader whose broker feed deviates randomly by up to ±1 pip from Dukascopy – truth CLEAN (risk: false flag)
- K9 quiet exploiter taking only 0.3 pip advantage per trade, below the 0.5 pip tolerance – truth EXPLOITER (risk: miss)

Rule v1 (unchanged, from VORAB.md): ≥ 3 trades that flip at the real market price with > 0.5 pip advantage.
Rule v2 (new, account level): ≥ 20 trades, mean price advantage vs market > 0.1 pip and t-value > 3. Random feed deviations average out; a small but constant advantage does not.

Honest history: on synthetic ticks v1 failed both stress cases (false flag on K8, miss on K9). Rule v2 was written AFTER seeing that, and scored 9/9 on synthetic ticks. It has not seen real ticks yet. This commit freezes v2 before the real-tick run; the result is published whatever it shows.

Prediction: v1 fails at least one of K8/K9 on real ticks; v2 is right on at least 8 of 9 accounts.
Known gap: v2 needs ≥ 20 trades; accounts with fewer trades are only covered by v1.
