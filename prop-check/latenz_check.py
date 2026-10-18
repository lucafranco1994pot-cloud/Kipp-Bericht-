#!/usr/bin/env python3
"""Ausfuehrungs-Check fuer Prop-Firmen (Demo mit bekannten Antworten).

Idee (Decision-Delta): Pro Trade wird genau EINE Sache ersetzt – der im Konto protokollierte
Einstiegspreis durch den echten Marktpreis zum selben Zeitpunkt (unabhaengige Tick-Daten).
Kippt ein Gewinn-Trade dadurch in Verlust UND war der protokollierte Preis besser als der Markt,
ist der Trade ein belegter Kandidat fuer 'Latency Arbitrage' (Gewinn aus veralteten Kursen).

Ablauf: Dukascopy-Ticks EURUSD laden -> 7 Test-Konten mit bekannter Wahrheit erzeugen ->
Baseline-Regel (Haltedauer) und Kipp-Check anwenden -> Bericht.
Aufruf: python latenz_check.py <ausgabeordner> [--synthetisch]"""
import lzma, struct, sys, urllib.request, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
import pandas as pd

PIP = 0.0001
TAGE = ['2025-03-03', '2025-03-04', '2025-03-05', '2025-03-06', '2025-03-07']
STUNDEN = range(7, 18)          # 07-17 UTC
SCHWELLE_VORTEIL = 0.5 * PIP    # Fill besser als Markt um mehr als 0,5 Pip (Toleranz fuer Feed-Unterschiede)
MIN_TRADES_AUFFAELLIG = 3

# ---------- Tick-Daten ----------
def lade_dukascopy():
    teile = []
    for tag in TAGE:
        d = datetime.fromisoformat(tag).replace(tzinfo=timezone.utc)
        for h in STUNDEN:
            url = f'https://datafeed.dukascopy.com/datafeed/EURUSD/{d.year}/{d.month-1:02d}/{d.day:02d}/{h:02d}h_ticks.bi5'
            for versuch in range(8):
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (research; kipp-bericht)'})
                    roh = urllib.request.urlopen(req, timeout=60).read(); time.sleep(1); break
                except Exception as e:
                    print('Wiederhole', url, type(e).__name__, e, flush=True); time.sleep(10 * (versuch + 1))
            else:
                raise RuntimeError(f'Download fehlgeschlagen: {url}')
            if not roh:
                continue
            a = np.frombuffer(lzma.decompress(roh), dtype=np.dtype([('ms', '>u4'), ('ask', '>u4'), ('bid', '>u4'), ('av', '>f4'), ('bv', '>f4')]))
            start = np.datetime64(d.replace(tzinfo=None) + timedelta(hours=h), 'ms')
            teile.append(pd.DataFrame({'t': start + a['ms'].astype('timedelta64[ms]'), 'bid': a['bid'] / 1e5, 'ask': a['ask'] / 1e5}))
    return pd.concat(teile, ignore_index=True)

def synthetische_ticks(seed=1):
    rng = np.random.default_rng(seed); rows = []
    for tag in TAGE:
        t0 = np.datetime64(tag + 'T07:00:00', 'ms'); n = 11 * 3600 * 4
        dt = rng.integers(100, 400, n).cumsum().astype('timedelta64[ms]')
        mid = 1.08 + np.cumsum(rng.normal(0, 0.00004, n))
        sp = 0.00008
        rows.append(pd.DataFrame({'t': t0 + dt, 'bid': mid - sp / 2, 'ask': mid + sp / 2}))
    return pd.concat(rows, ignore_index=True)

class Markt:
    def __init__(self, ticks):
        self.t = ticks['t'].values.astype('datetime64[ms]'); self.bid = ticks['bid'].values; self.ask = ticks['ask'].values
    def idx(self, t):
        return max(np.searchsorted(self.t, np.datetime64(t, 'ms'), side='right') - 1, 0)
    def kauf(self, t):  return self.ask[self.idx(t)]
    def verkauf(self, t): return self.bid[self.idx(t)]
    def mitte(self, t):
        i = self.idx(t); return (self.bid[i] + self.ask[i]) / 2
    def einstieg(self, t, r): return self.kauf(t) if r > 0 else self.verkauf(t)
    def ausstieg(self, t, r): return self.verkauf(t) if r > 0 else self.kauf(t)

S = np.timedelta64(1, 's')

def trade(m, r, t_in, t_out, preis_in=None):
    return dict(Richtung=int(r), Eroeffnung=t_in, Schliessung=t_out,
                Preis_Eroeffnung=float(m.einstieg(t_in, r) if preis_in is None else preis_in),
                Preis_Schliessung=float(m.ausstieg(t_out, r)))

# ---------- Test-Konten (bekannte Wahrheit) ----------
def ausnutzer(m, halten=5 * S, jede=1):
    """Fills zum Kurs von vor 1 Sekunde (veralteter Feed) nach Sprung >= 1,5 Pip."""
    out, sperre, n = [], m.t[0], 0
    for i in range(0, len(m.t), 3):
        t = m.t[i]
        if t < sperre: continue
        alt = m.mitte(t - S); jetzt = (m.bid[i] + m.ask[i]) / 2
        if abs(jetzt - alt) >= 1.5 * PIP:
            r = 1 if jetzt > alt else -1; n += 1
            if n % jede == 0:
                out.append(trade(m, r, t, t + halten, preis_in=m.einstieg(t - S, r)))
            sperre = t + 60 * S
    return out

def scalper(m):
    """Echte Fills: Einstieg nach 3-Pip-Bewegung in 60 s, Ziel/Stop 3 Pip, max. 120 s."""
    out, sperre = [], m.t[0]
    for i in range(0, len(m.t), 5):
        t = m.t[i]
        if t < sperre: continue
        bew = (m.bid[i] + m.ask[i]) / 2 - m.mitte(t - 60 * S)
        if abs(bew) >= 3 * PIP:
            r = 1 if bew > 0 else -1; p = m.einstieg(t, r); ende = t + 120 * S
            j = i
            while j < len(m.t) and m.t[j] < ende:
                x = m.bid[j] if r > 0 else m.ask[j]
                if (x - p) * r >= 3 * PIP or (x - p) * r <= -3 * PIP: ende = m.t[j]; break
                j += 1
            out.append(trade(m, r, t, ende)); sperre = ende + 300 * S
    return out

def swing(m, rauschen=0.0, seed=7):
    """Echte Fills: jede volle Stunde Richtung der letzten Stunde, 3 h halten."""
    rng = np.random.default_rng(seed); out = []
    for tag in TAGE:
        for h in range(8, 15, 3):
            t = np.datetime64(f'{tag}T{h:02d}:00:00', 'ms')
            r = 1 if m.mitte(t) > m.mitte(t - 3600 * S) else -1
            p = m.einstieg(t, r) + (rng.uniform(-rauschen, rauschen) if rauschen else 0)
            out.append(trade(m, r, t, t + 3 * 3600 * S, preis_in=p))
    return out

def news(m):
    """Echte Fills, sehr kurz: zur Minute 30 jeder Stunde, wenn 10-s-Bewegung >= 2 Pip, 20 s halten."""
    out = []
    for tag in TAGE:
        for h in STUNDEN:
            for s in range(0, 120, 2):
                t = np.datetime64(f'{tag}T{h:02d}:30:00', 'ms') + s * S
                bew = m.mitte(t) - m.mitte(t - 10 * S)
                if abs(bew) >= 2 * PIP:
                    r = 1 if bew > 0 else -1
                    out.append(trade(m, r, t, t + 20 * S)); break
    if len(out) < 10:   # ruhige Tage: zusaetzlich jede Stunde zur Minute 30, Richtung der letzten 10 s
        for tag in TAGE:
            for h in STUNDEN:
                t = np.datetime64(f'{tag}T{h:02d}:30:00', 'ms')
                r = 1 if m.mitte(t) >= m.mitte(t - 10 * S) else -1
                out.append(trade(m, r, t, t + 20 * S))
    return out

def konten(m):
    return {
        'K1 Latenz-Ausnutzer (5 s)':             (ausnutzer(m), True),
        'K2 Scalper, echte Fills':               (scalper(m), False),
        'K3 Swing-Trader, echte Fills':          (swing(m), False),
        'K4 Swing + versteckte Ausnutzer-Trades':(swing(m) + ausnutzer(m, jede=10), True),
        'K5 Schneller News-Trader, echte Fills': (news(m), False),
        'K6 Swing mit Slippage-Rauschen +-0,3 Pip':(swing(m, rauschen=0.3 * PIP), False),
        'K7 Ausnutzer, 10 Min. halten (getarnt)':(ausnutzer(m, halten=600 * S), True),
    }

# ---------- Pruefungen ----------
def baseline(df):
    halt = (pd.to_datetime(df.Schliessung) - pd.to_datetime(df.Eroeffnung)).dt.total_seconds()
    return bool(halt.median() < 60 or (halt < 30).mean() >= 0.5)

def kipp_check(m, df):
    rows = []
    for _, x in df.iterrows():
        r = x.Richtung; markt = m.einstieg(x.Eroeffnung, r)
        vorteil = (markt - x.Preis_Eroeffnung) * r
        g_protokoll = (x.Preis_Schliessung - x.Preis_Eroeffnung) * r
        g_markt = (x.Preis_Schliessung - markt) * r
        verz = {f'Gewinn_bei_{d}s_Pips': round((x.Preis_Schliessung - m.einstieg(x.Eroeffnung + d * S, r)) * r / PIP, 2) for d in (1, 3, 10)}
        kippt = bool(vorteil > SCHWELLE_VORTEIL and g_protokoll > 0 and g_markt <= 0)
        rows.append(dict(Eroeffnung=str(x.Eroeffnung), Richtung=r, Vorteil_ggu_Markt_Pips=round(vorteil / PIP, 2),
                         Gewinn_Protokoll_Pips=round(g_protokoll / PIP, 2), Gewinn_Marktpreis_Pips=round(g_markt / PIP, 2),
                         **verz, Kippt=kippt))
    t = pd.DataFrame(rows)
    return t, int(t.Kippt.sum()) >= MIN_TRADES_AUFFAELLIG

def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    ticks = synthetische_ticks() if '--synthetisch' in sys.argv else lade_dukascopy()
    m = Markt(ticks)
    zeilen = []
    for name, (trades, wahr) in konten(m).items():
        df = pd.DataFrame(trades)
        b = baseline(df); t, k = kipp_check(m, df)
        t.to_csv(out / f"trades_{name.split()[0]}.csv", index=False)
        zeilen.append(dict(Konto=name, Trades=len(df), Wahrheit='AUSNUTZER' if wahr else 'SAUBER',
                           Baseline='AUFFAELLIG' if b else 'unauffaellig', Baseline_richtig=b == wahr,
                           Kipp_Check='AUFFAELLIG' if k else 'unauffaellig', Kipp_Check_richtig=k == wahr,
                           Gekippte_Trades=int(t.Kippt.sum()),
                           Gewinn_Protokoll_Pips=round(t.Gewinn_Protokoll_Pips.sum(), 1),
                           Gewinn_Marktpreis_Pips=round(t.Gewinn_Marktpreis_Pips.sum(), 1)))
    z = pd.DataFrame(zeilen); z.to_csv(out / 'zusammenfassung.csv', index=False)
    txt = (f"# Ausfuehrungs-Check Demo – Ergebnis\nTicks: {len(ticks)} ({'synthetisch' if '--synthetisch' in sys.argv else 'Dukascopy EURUSD'}), Tage {TAGE[0]} bis {TAGE[-1]}, 07-18 UTC\n\n"
           + z.to_markdown(index=False) + f"\n\nBaseline richtig: {int(z.Baseline_richtig.sum())}/{len(z)}  |  Kipp-Check richtig: {int(z.Kipp_Check_richtig.sum())}/{len(z)}\n")
    (out / 'ERGEBNIS.md').write_text(txt, encoding='utf-8'); print(txt)

if __name__ == '__main__':
    main()
