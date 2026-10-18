#!/usr/bin/env python3
"""Vergleicht zwei Freqtrade-Backtests Trade fuer Trade.
Aufruf: python vergleich.py <ordner_A> <ordner_B> <name> <ausgabeordner> [versatz_minuten]
versatz_minuten: Original-Einstiege werden fuer den Abgleich um so viele Minuten verschoben (fuer Verzoegerungs-Varianten)."""
import sys
from pathlib import Path
import pandas as pd
from freqtrade.data.btanalysis import load_backtest_data

COLS = ['pair', 'open_date', 'close_date', 'exit_reason', 'profit_ratio', 'profit_abs']

def lade(d):
    files = sorted(x for x in Path(d).glob('backtest-result-*') if x.suffix == '.zip' or (x.suffix == '.json' and not x.name.endswith('.meta.json')))
    print('Ergebnisdateien in', d, ':', [x.name for x in files])
    if len(files) != 1:
        raise ValueError(f'Erwarte genau eine Ergebnisdatei in {d}, gefunden: {len(files)}')
    df = load_backtest_data(files[0])
    if df.empty:
        return pd.DataFrame(columns=COLS)
    df = df[['pair', 'open_date', 'close_date', 'exit_reason', 'profit_ratio', 'profit_abs']].copy()
    df['open_date'] = pd.to_datetime(df['open_date'], utc=True)
    df['close_date'] = pd.to_datetime(df['close_date'], utc=True)
    return df

def vergleiche(a, b):
    m = a.merge(b, on=['pair', 'open_date'], how='outer', suffixes=('_A', '_B'), indicator=True)
    rows = []
    for _, r in m.iterrows():
        if r['_merge'] == 'left_only':
            art = 'Trade nur im Original'
        elif r['_merge'] == 'right_only':
            art = 'Trade nur in der Variante'
        elif r['close_date_A'] != r['close_date_B'] or r['exit_reason_A'] != r['exit_reason_B']:
            art = 'gleicher Einstieg, anderer Ausstieg'
        else:
            continue
        rows.append(dict(Paar=r['pair'], Einstieg=r['open_date'], Art=art,
                         Ausstieg_A=r.get('close_date_A'), Grund_A=r.get('exit_reason_A'), Gewinn_A=r.get('profit_abs_A'),
                         Ausstieg_B=r.get('close_date_B'), Grund_B=r.get('exit_reason_B'), Gewinn_B=r.get('profit_abs_B')))
    d = pd.DataFrame(rows)
    if not d.empty:
        d = d.sort_values(['Paar', 'Einstieg'])
        d['Einordnung'] = 'moegliche Folgewirkung'
        d.loc[d.groupby('Paar').head(1).index, 'Einordnung'] = 'erste Kippstelle dieses Paares'
    return d

def main():
    da, db, name, out = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    a, b = lade(da), lade(db)
    off = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    if off:
        a['open_date'] = a['open_date'] + pd.Timedelta(minutes=off)
        name = f'{name} (Abgleich mit {off} Min. Versatz)'
    d = vergleiche(a, b)
    d.to_csv(out / f'kipps_{name}.csv', index=False)
    n = len(d)
    txt = (f'## {name}\n- Trades Original: {len(a)}, Variante: {len(b)}\n'
           f'- Gewinn Original: {a.profit_abs.sum():.2f} USDT, Variante: {b.profit_abs.sum():.2f} USDT\n'
           f'- Gekippte Trade-Entscheidungen: {n}'
           + (f" (davon {int((d.Art=='Trade nur im Original').sum())} weggefallen, "
              f"{int((d.Art=='Trade nur in der Variante').sum())} neu, "
              f"{int((d.Art=='gleicher Einstieg, anderer Ausstieg').sum())} anderer Ausstieg; "
              f"{int((d.Einordnung=='erste Kippstelle dieses Paares').sum())} erste Kippstellen)" if n else '')
           + f'\n- Anteil gekippt: {n / max(len(a), 1):.1%} der Original-Trades\n\n')
    with open(out / 'ZUSAMMENFASSUNG.md', 'a', encoding='utf-8') as f:
        f.write(txt)
    print(txt)

if __name__ == '__main__':
    main()
