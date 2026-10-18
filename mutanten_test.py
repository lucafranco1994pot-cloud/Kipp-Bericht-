#!/usr/bin/env python3
"""Mutationstest: Baut absichtlich fehlerhafte Programmversionen und prueft,
ob die 10 Tests sie erkennen. Gute Tests muessen jede Fehlversion durchfallen lassen."""
import sys, importlib, tempfile
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import kipp_beweis as K
ORIG = {n: getattr(K, n) for n in ('cause', 'validate', 'analyse', 'position_effects')}

def cause_50(a, b, dt):  # Fehler: nur 50 statt 51 Schlusskurse geprueft
    i = a.index.get_loc(dt); a2 = a.iloc[max(0, i-49):]; b2 = b.loc[a2.index]
    pad = a.iloc[:max(0, i-49)]
    return ORIG['cause'](pd.concat([pad, a2]), pd.concat([pad, b2]), dt)

def cause_ungeprueft(a, b, dt):  # Fehler: erste Aenderung = Ursache, ohne Ruecktausch-Pruefung
    i = a.index.get_loc(dt)
    for j in range(max(0, i-50), i+1):
        w = a.index[j]
        if not K.equal(a.at[w, 'Close'], b.at[w, 'Close']):
            return dict(Kategorie='einzelner Rücktausch stellt Original wieder her', Ursache_Datum=str(w.date()),
                        Feld='Close', Alter_Wert=0, Neuer_Wert=0, Einzel_Ruecktausch_Treffer=1, Weitere_Treffer='', Kandidaten=1)
    return dict(Kategorie='einzelner Rücktausch stellt Original wieder her', Ursache_Datum=str(dt.date()),
                Feld='Close', Alter_Wert=0, Neuer_Wert=0, Einzel_Ruecktausch_Treffer=1, Weitere_Treffer='', Kandidaten=1)

def validate_fuellt(df):  # Fehler: fehlende Werte werden still aufgefuellt
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce').ffill()

def analyse_positionsweise(a, b, t):  # Fehler: Zeilen nach Position statt Datum vergleichen
    n = min(len(a), len(b)); b2 = b.iloc[:n].copy(); b2.index = a.index[:n]
    return ORIG['analyse'](a.iloc[:n], b2, t)

def analyse_positionen_als_kipps(a, b, t):  # Fehler: Positionsfolgen als Kipps gezaehlt
    r = ORIG['analyse'](a, b, t)
    r['flips'] = r['flips'] + [dict(Datum=x['Datum'], Ursache_Datum='') for x in r['positions'] if x['Typ'] == 'reine Positionsfolgewirkung']
    return r

def decision_ohne_gleich(df):  # Fehler: Kreuzung nur bei strikt < statt <=
    c = pd.to_numeric(df['Close'], errors='coerce'); d = c.rolling(20, min_periods=20).mean() - c.rolling(50, min_periods=50).mean()
    v = d.notna() & d.shift().notna(); out = pd.Series(K.INVALID, index=df.index, dtype=object); out.loc[v] = K.NONE
    out.loc[v & (d > 0) & (d.shift() < 0)] = K.BUY; out.loc[v & (d < 0) & (d.shift() > 0)] = K.SELL
    return pd.DataFrame({'SMA20': None, 'SMA50': None, 'Entscheidung': out})

MUTANTEN = {
    'M1 nur 50 statt 51 Kurse': ('cause', cause_50),
    'M2 Ursache ohne Ruecktausch-Pruefung': ('cause', cause_ungeprueft),
    'M3 fehlende Kurse still auffuellen': ('validate', validate_fuellt),
    'M4 Zeilen nach Position statt Datum': ('analyse', analyse_positionsweise),
    'M5 Positionsfolgen als Kipps zaehlen': ('analyse', analyse_positionen_als_kipps),
    'M6 Kreuzung ohne Gleichheit (< statt <=)': ('decision', decision_ohne_gleich),
}

rows = []
for name, (fn, mut) in MUTANTEN.items():
    saved = getattr(K, fn); setattr(K, fn, mut)
    try:
        with tempfile.TemporaryDirectory() as d:
            try:
                df = K.tests(Path(d)); failed = list(df.Test[df.Richtig != 'JA'])
            except RuntimeError:
                df = pd.read_csv(Path(d) / 'tests.csv'); failed = list(df.Test[df.Richtig != 'JA'])
    finally:
        setattr(K, fn, saved)
    rows.append(dict(Fehlversion=name, Erkannt='JA' if failed else 'NEIN', Durchgefallene_Tests='; '.join(failed) or '-'))

res = pd.DataFrame(rows)
print('\n' + res.to_string(index=False))
print(f"\nErkannt: {(res.Erkannt=='JA').sum()} von {len(res)} Fehlversionen")
res.to_csv(Path(__file__).parent / 'mutanten_ergebnis.csv', index=False, encoding='utf-8-sig')
