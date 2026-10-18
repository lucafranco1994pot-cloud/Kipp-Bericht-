#!/usr/bin/env python3
"""Fahrtenschreiber: speichert taeglich die Schlusskurse (Close, repair=False) der 30 festen Aktien
und vergleicht sie mit dem vorherigen Schnappschuss. Nachtraegliche Aenderungen alter Kurse werden
protokolliert; dann wird geprueft, ob die feste SMA20/SMA50-Entscheidung dadurch kippt.
Nur Close wird gespeichert (Strategieeingang), keine vollstaendigen Rohdaten."""
import sys, hashlib, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from kipp_beweis import TICKERS, decision, INVALID

ROOT = Path(__file__).parent / 'fahrtenschreiber'
SNAP = ROOT / 'schnappschuesse'
TOL = 1e-9  # relative Toleranz: Rundungsreste (~1e-16) zaehlen nicht als Aenderung

def download():
    import yfinance as yf
    cols, errs = {}, []
    for t in TICKERS:
        try:
            df = yf.download(t, period='1y', interval='1d', auto_adjust=False, repair=False,
                             progress=False, threads=False, multi_level_index=False, timeout=30)
            if df is None or df.empty: raise ValueError('leer')
            idx = pd.DatetimeIndex(df.index)
            if idx.tz is not None: idx = idx.tz_localize(None)
            s = pd.Series(pd.to_numeric(df['Close'], errors='coerce').values, index=idx.normalize())
            cols[t] = s[~s.index.duplicated(keep='last')]
        except Exception as e:
            errs.append(f'{t}: {type(e).__name__}: {e}')
        time.sleep(1)
    wide = pd.DataFrame(cols).sort_index()
    wide.index.name = 'Date'
    return wide, errs

def main():
    SNAP.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    prev_files = sorted(SNAP.glob('close_*.csv.gz'))
    new, errs = download()
    # Heutige, noch laufende Kerze nicht speichern: nur Tage vor dem Abrufdatum (UTC)
    new = new[new.index < pd.Timestamp(datetime.now(timezone.utc).date())]
    fn = SNAP / f'close_{stamp}.csv.gz'
    new.to_csv(fn, float_format='%.17g', compression='gzip')
    digest = hashlib.sha256(fn.read_bytes()).hexdigest()
    with open(ROOT / 'protokoll.csv', 'a', encoding='utf-8') as f:
        if f.tell() == 0: f.write('Abruf_UTC,Datei,SHA256,Aktien_OK,Fehler\n')
        f.write(f'{stamp},{fn.name},{digest},{new.shape[1]},"{" | ".join(errs)}"\n')
    if not prev_files:
        print('Erster Schnappschuss gespeichert, noch kein Vergleich.'); return
    old = pd.read_csv(prev_files[-1], index_col='Date', parse_dates=['Date'], compression='gzip')
    changes, flips = [], []
    for t in sorted(set(old.columns) & set(new.columns)):
        a, b = old[t].dropna(), new[t].dropna()
        common = a.index.intersection(b.index)
        if len(common) == 0: continue
        lo = max(a.index.min(), b.index.min()); hi = min(a.index.max(), b.index.max())
        ra = a[(a.index >= lo) & (a.index <= hi)]; rb = b[(b.index >= lo) & (b.index <= hi)]
        rows_changed = not ra.index.equals(rb.index)
        if rows_changed:
            for d in ra.index.symmetric_difference(rb.index):
                changes.append(dict(Abruf_UTC=stamp, Aktie=t, Datum=str(d.date()), Alt='fehlt' if d not in ra.index else ra[d],
                                    Neu='fehlt' if d not in rb.index else rb[d], Art='ZEILE'))
        rel = (b[common] / a[common] - 1).abs()
        for d in rel[rel > TOL].index:
            changes.append(dict(Abruf_UTC=stamp, Aktie=t, Datum=str(d.date()), Alt=a[d], Neu=b[d], Art='CLOSE'))
        if (rel > TOL).any() and not rows_changed:
            da = decision(pd.DataFrame({'Close': ra})); db = decision(pd.DataFrame({'Close': rb}))
            for d in ra.index:
                x, y = da.at[d, 'Entscheidung'], db.at[d, 'Entscheidung']
                if x != y and INVALID not in (x, y):
                    flips.append(dict(Abruf_UTC=stamp, Aktie=t, Datum=str(d.date()), Vorher=x, Nachher=y))
        elif (rel > TOL).any():
            flips.append(dict(Abruf_UTC=stamp, Aktie=t, Datum='', Vorher='', Nachher='', Hinweis='Zeilen geaendert: Kipp-Pruefung manuell'))
    for name, rows in (('aenderungen.csv', changes), ('kipps.csv', flips)):
        if rows:
            p = ROOT / name
            pd.DataFrame(rows).to_csv(p, mode='a', header=not p.exists(), index=False, float_format='%.17g')
    print(f'Vergleich mit {prev_files[-1].name}: {len(changes)} nachtraegliche Aenderungen, {len(flips)} Kipps.')

if __name__ == '__main__':
    main()
