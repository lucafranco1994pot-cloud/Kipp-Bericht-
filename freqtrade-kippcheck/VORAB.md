# Kipp-Check Beispiel 1 – vorab festgelegt (18.10.2026)

Frage: Welche einzelnen Trades der offiziellen Freqtrade-Beispielstrategie kippen, wenn sich genau eine Sache aendert?

Fest vor dem ersten Lauf:
- Strategie: `strategies/sample_strategy.py` (unveraenderte Kopie der Freqtrade-Vorlage, Version 2026.9; SHA-256 im Lauf protokolliert)
- Daten: OKX Spot, 5m, BTC/USDT, ETH/USDT, SOL/USDT, Zeitraum 01.01.2025–31.12.2025 (Binance sperrt die GitHub-Server)
- Einsatz 100 USDT, max. 3 offene Trades, Startkapital 1000 USDT (`config.json`)
- A Original: Gebuehr 0,1 % pro Seite
- B Doppelte Gebuehr: 0,2 % pro Seite, sonst gleich
- C Eine Kerze Verzoegerung: jedes Signal eine Kerze spaeter (`strategies/kipp_verzoegerung.py`), Gebuehr 0,1 %
- Vergleich Trade fuer Trade ueber (Paar, Einstiegszeit): weggefallen / neu / anderer Ausstieg (`vergleich.py`)
- Pro Paar wird die erste Abweichung als "erste Kippstelle" markiert, spaetere als "moegliche Folgewirkung"

Nichts davon wird nach Sichtung der Ergebnisse geaendert. Kein Renditeversprechen, keine Anlageberatung.
