#!/usr/bin/env python3
"""Decision-Delta: fixed SMA20/SMA50 daily-close experiment."""
import argparse, csv, hashlib, html, json, platform, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

TICKERS = ['AAPL','MSFT','NVDA','AMZN','GOOGL','META','TSLA','JPM','XOM','KO',
'0005.HK','0700.HK','1398.HK','0939.HK','0941.HK','1299.HK','2318.HK','0388.HK','0883.HK','3988.HK',
'HSBA.L','BP.L','SHEL.L','AZN.L','ULVR.L','GSK.L','RIO.L','BARC.L','LLOY.L','VOD.L']
START, END_EXCLUSIVE = '2020-01-01', '2025-01-01'
BUY, SELL, NONE, INVALID = 'KAUF', 'VERKAUF', 'KEINE AKTION', 'NICHT BERECHENBAR'
FIELDS = ['Open','High','Low','Close','Adj Close','Volume','Dividends','Stock Splits','Capital Gains']
WARNING = ('Vergleich repair=False gegen repair=True, KEIN Nachweis einer nachtraeglichen '
'Anbieter-Korrektur oder eines echten ausgefuehrten Trades. Reparaturen koennen falsch sein. '
'Getrennte Abrufe koennen zusaetzlich unterschiedliche Anbieterantworten enthalten. '
'Close wird mit auto_adjust=False benutzt; Adj Close ist kein Strategieeingang. '
'Yahoo Close ist trotzdem nicht garantiert historisch unbereinigt (z.B. Splits).')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write_csv(df, path):
    df.to_csv(path, index=False, encoding='utf-8-sig', float_format='%.17g')

def decision(df):
    c = pd.to_numeric(df['Close'], errors='coerce')
    a = c.rolling(20, min_periods=20).mean()
    b = c.rolling(50, min_periods=50).mean()
    d = a-b
    valid = d.notna() & d.shift().notna()
    out = pd.Series(INVALID, index=df.index, dtype=object)
    out.loc[valid] = NONE
    out.loc[valid & (d>0) & (d.shift()<=0)] = BUY
    out.loc[valid & (d<0) & (d.shift()>=0)] = SELL
    return pd.DataFrame({'SMA20':a,'SMA50':b,'Entscheidung':out})

def equal(a,b):
    if pd.isna(a) and pd.isna(b): return True
    if pd.isna(a) or pd.isna(b): return False
    return bool(a == b)

def field_diffs(a,b,ticker='TEST'):
    rows=[]
    for dt in a.index.union(b.index).sort_values():
        if dt not in a.index or dt not in b.index:
            rows.append(dict(Aktie=ticker, Datum=str(dt.date()), Feld='ZEILE_FEHLT',
                Original='vorhanden' if dt in a.index else 'fehlt',
                Repariert='vorhanden' if dt in b.index else 'fehlt'))
            continue
        for field in FIELDS:
            if field not in a and field not in b: continue
            av = a.at[dt,field] if field in a else np.nan
            bv = b.at[dt,field] if field in b else np.nan
            if not equal(av,bv):
                rows.append(dict(Aktie=ticker,Datum=str(dt.date()),Feld=field,Original=av,Repariert=bv))
    return rows

def validate(df):
    if not isinstance(df.index,pd.DatetimeIndex): raise ValueError('Kein Datumsindex')
    if df.index.has_duplicates: raise ValueError('Doppelte Handelstage')
    if not df.index.is_monotonic_increasing: raise ValueError('Nicht chronologisch')
    if 'Close' not in df: raise ValueError('Close fehlt')
    x=pd.to_numeric(df.Close,errors='coerce')
    if x.isna().any() or not np.isfinite(x).all() or (x<=0).any():
        raise ValueError('Close fehlt, ist unendlich oder nicht positiv; keine Auffuellung erlaubt')

def cause(a,b,dt):
    """Individual reversion, oldest date first. Includes previous 50 sessions AND today."""
    i=a.index.get_loc(dt)
    expected=decision(a).at[dt,'Entscheidung']
    candidates=[]
    for j in range(max(0,i-50),i+1):
        when=a.index[j]
        av,bv=a.at[when,'Close'],b.at[when,'Close']
        if not equal(av,bv): candidates.append((when,av,bv))
    if not candidates:
        return dict(Kategorie='keine Datenursache',Ursache_Datum='',Feld='',Alter_Wert='',Neuer_Wert='',
                    Einzel_Ruecktausch_Treffer=0,Weitere_Treffer='',Kandidaten=0)
    hits=[]
    for when,av,bv in candidates:
        trial=b.copy(deep=True)
        trial.at[when,'Close']=av
        if decision(trial).at[dt,'Entscheidung']==expected: hits.append((when,av,bv))
    if not hits:
        return dict(Kategorie='mehrere Änderungen wirken zusammen',Ursache_Datum='',Feld='',
                    Alter_Wert='',Neuer_Wert='',Einzel_Ruecktausch_Treffer=0,Weitere_Treffer='',
                    Kandidaten=len(candidates))
    when,av,bv=hits[0]
    # A reverse-direction test distinguishes a restoring value from a sufficient cause.
    forward=a.copy(deep=True); forward.at[when,'Close']=bv
    sufficient=decision(forward).at[dt,'Entscheidung']==decision(b).at[dt,'Entscheidung']
    return dict(Kategorie='einzelner Rücktausch stellt Original wieder her',
        Ursache_Datum=str(when.date()),Feld='Close',Alter_Wert=float(av),Neuer_Wert=float(bv),
        Einzel_Ruecktausch_Treffer=len(hits),
        Weitere_Treffer='; '.join(str(x[0].date()) for x in hits[1:]),
        Kandidaten=len(candidates),Auch_vorwaerts_ausreichend=bool(sufficient))

def position_effects(da,db):
    """Separate illustrative long/flat state; does NOT change fixed signal strategy."""
    pa=pb=0; rows=[]
    for dt in da.index:
        x,y=da.at[dt,'Entscheidung'],db.at[dt,'Entscheidung']
        if x==INVALID or y==INVALID: continue
        if x==BUY: pa=1
        elif x==SELL: pa=0
        if y==BUY: pb=1
        elif y==SELL: pb=0
        if pa!=pb:
            rows.append(dict(Datum=str(dt.date()),Original_Position=pa,Repariert_Position=pb,
                Typ='reine Positionsfolgewirkung' if x==y else 'direkter Signalunterschied'))
    return rows

def analyse(a,b,ticker):
    validate(a);validate(b)
    diffs=field_diffs(a,b,ticker)
    da,db=decision(a),decision(b)
    if not a.index.equals(b.index):
        return dict(status='BLOCKIERT: unterschiedliche Handelstage; keine Kausalzuordnung',
                    diffs=diffs,flips=[],positions=[],original=da,repaired=db,comparable=0)
    rows=[]; first=''
    for dt in a.index:
        x,y=da.at[dt,'Entscheidung'],db.at[dt,'Entscheidung']
        if x==INVALID or y==INVALID or x==y: continue
        if not first: first=str(dt.date())
        row=dict(Aktie=ticker,Datum=str(dt.date()),Original=x,Repariert=y,
                 Einordnung='erste direkte Kipp-Entscheidung' if str(dt.date())==first else 'weiterer direkter Signalunterschied',
                 Erste_Kippentscheidung=first)
        row.update(cause(a,b,dt));rows.append(row)
    return dict(status='OK',diffs=diffs,flips=rows,positions=position_effects(da,db),
                original=da,repaired=db,
                comparable=int(((da.Entscheidung!=INVALID)&(db.Entscheidung!=INVALID)).sum()))

def artificial():
    dates=pd.bdate_range('2020-01-01',periods=71)
    base=pd.DataFrame({'Close':100.,'Volume':1000.},index=dates)
    return base

def tests(out):
    out.mkdir(parents=True,exist_ok=True)
    records=[]
    def check(name,expected,fn):
        try:
            actual,ok=fn()
        except Exception as e: actual,ok=repr(e),False
        records.append(dict(Test=name,Erwartet=expected,Tatsaechlich=str(actual),Richtig='JA' if ok else 'NEIN'))
    def nflip(a,b): return len(analyse(a,b,'SYNTHETISCH')['flips'])
    a=artificial();b=a.copy()
    check('01 Identische Daten','0 Kipps',lambda:(nflip(a,b),nflip(a,b)==0))
    a=artificial();b=a.copy();b.iloc[-1,b.columns.get_loc('Volume')]=999999
    check('02 Nur Volumen geaendert','1 Datenunterschied; 0 Kipps',
        lambda:((len(field_diffs(a,b)),nflip(a,b)),len(field_diffs(a,b))==1 and nflip(a,b)==0))
    a=artificial();b=a.copy();b.iloc[-1,0]=110
    def single():
        r=analyse(a,b,'SYNTHETISCH')['flips']; ok=len(r)==1 and r[0]['Ursache_Datum']==str(a.index[-1].date()) and r[0]['Feld']=='Close' and r[0]['Original']==NONE and r[0]['Repariert']==BUY
        return [(x['Datum'],x['Original'],x['Repariert'],x['Ursache_Datum']) for x in r],ok
    check('03 Ein Close verschiebt Kreuzung','genau 1 Kipp, letzte Kerze als Ursache',single)
    a=artificial();a.iloc[-2,0]=99;a.iloc[-1,0]=103;b=a.copy();b.iloc[-26,0]=110;b.iloc[-27,0]=110
    def jointly():
        c=cause(a,b,a.index[-1]);x=decision(a).iloc[-1].Entscheidung;y=decision(b).iloc[-1].Entscheidung
        return (x,y,c['Kategorie']),x==BUY and y==NONE and c['Kategorie']=='mehrere Änderungen wirken zusammen'
    check('04 Zwei Ruecktausche erforderlich','KAUF -> KEINE AKTION; mehrere Änderungen wirken zusammen',jointly)
    a=artificial();b=a.copy();b.iloc[-61,0]=200
    def outside():
        c=cause(a,b,a.index[-1]);return c['Kategorie'],c['Kategorie']=='keine Datenursache' and decision(a).iloc[-1].Entscheidung==decision(b).iloc[-1].Entscheidung
    check('05 Aenderung 60 Handelstage vorher','am Zieldatum keine Datenursache, gleiche Entscheidung',outside)
    a=artificial();b=a.copy();b.iloc[-1,0]=10000
    check('06 100-facher Einzelpreis','1 Kipp, letzter Close als Ursache',
        lambda:((nflip(a,b),cause(a,b,a.index[-1])['Ursache_Datum']),nflip(a,b)==1 and cause(a,b,a.index[-1])['Ursache_Datum']==str(a.index[-1].date())))
    a=artificial();b=a.drop(a.index[-10])
    def missing():
        r=analyse(a,b,'SYNTHETISCH');return (r['status'],len(r['flips']),len(r['diffs'])),r['status'].startswith('BLOCKIERT') and len(r['flips'])==0 and any(x['Feld']=='ZEILE_FEHLT' for x in r['diffs'])
    check('07 Fehlender Handelstag','BLOCKIERT; ZEILE_FEHLT; keine scheinbaren Kipps',missing)
    a=artificial();a.iloc[-2,0]=101;b=a.copy();b.iloc[-51,0]=110
    def boundary():
        c=cause(a,b,a.index[-1]);x=decision(a).iloc[-1].Entscheidung;y=decision(b).iloc[-1].Entscheidung
        return (x,y,c['Ursache_Datum']),x==NONE and y==BUY and c['Ursache_Datum']==str(a.index[-51].date())
    check('08 Rand t-50 beeinflusst gestrigen SMA50','KEINE AKTION -> KAUF; Ursache genau t-50',boundary)
    a=artificial();b=a.copy();b.iloc[60,0]=110
    def carry():
        r=analyse(a,b,'SYNTHETISCH');dt=str(a.index[61].date())
        p=[x for x in r['positions'] if x['Datum']==dt]
        s=[x for x in r['flips'] if x['Datum']==dt]
        return (p,len(s)),len(s)==0 and len(p)==1 and p[0]['Typ']=='reine Positionsfolgewirkung'
    check('09 Position wirkt nach, Signal nicht','Folgewirkung im Positionsprotokoll; kein Signal-Kipp an t+1',carry)
    a=artificial();b=a.copy();b.iloc[-1,0]=np.nan
    def invalid():
        try: analyse(a,b,'SYNTHETISCH'); return 'falsch akzeptiert',False
        except ValueError: return 'BLOCKIERT: fehlender Close',True
    check('10 Fehlender Close darf nicht aufgefuellt werden','BLOCKIERT',invalid)
    df=pd.DataFrame(records);write_csv(df,out/'tests.csv')
    (out/'tests.html').write_text('<meta charset="utf-8"><h1>10 kuenstliche Tests</h1><p>Keine Marktdaten.</p>'+df.to_html(index=False,escape=True),encoding='utf-8')
    print(df[['Test','Richtig']].to_string(index=False))
    if (df.Richtig!='JA').any(): raise RuntimeError('Mindestens ein Test fehlgeschlagen: kein Marktdatenlauf erlaubt')
    return df

def normalise(df):
    if df is None or df.empty: raise ValueError('Leere Anbieterantwort')
    df=df.copy()
    if isinstance(df.columns,pd.MultiIndex):
        if df.columns.nlevels==2: df.columns=df.columns.get_level_values(0)
        else: raise ValueError('Unerwarteter MultiIndex')
    idx=pd.DatetimeIndex(df.index)
    if idx.tz is not None: idx=idx.tz_localize(None)
    df.index=idx.normalize();df.index.name='Date'
    return df

def run(root):
    import yfinance as yf
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out=root/('lauf_'+stamp);out.mkdir(parents=True,exist_ok=False)
    tests(out/'tests')
    manifest=dict(created_utc=stamp,tickers=TICKERS,start=START,end_inclusive='2024-12-31',
        end_exclusive=END_EXCLUSIVE,interval='1d',auto_adjust=False,back_adjust=False,
        actions=True,keepna=True,repair=[False,True],strategy='SMA20 crosses SMA50; Close; no positions',
        warmup='Keine Daten vor 2020; erste 50 Zeilen ohne Entscheidung',
        causal_window='50 vorherige Handelstage PLUS Zieldatum = 51 Schlusskurse',
        candidate_order='Datum aufsteigend; Feld Close',float_comparison='exakt; CSV roundtrip 17 Stellen',
        python=sys.version,pandas=pd.__version__,numpy=np.__version__,yfinance=yf.__version__,
        warning=WARNING,source_sha256=sha(__file__),downloads=[],scope='Keine Strategieaenderung; keine Ausfuehrung/PnL')
    (out/'experiment_vorab.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    summaries=[];alld=[];allf=[];allp=[]
    for ticker in TICKERS:
        print('Lade',ticker,flush=True);data={};errs=[]
        for repaired in (False,True):
            mode='repair_true' if repaired else 'repair_false'
            begin=datetime.now(timezone.utc).isoformat()
            record=dict(ticker=ticker,repair=repaired,started_utc=begin)
            try:
                df=yf.download(ticker,start=START,end=END_EXCLUSIVE,interval='1d',
                    auto_adjust=False,back_adjust=False,repair=repaired,actions=True,keepna=True,
                    threads=False,progress=False,multi_level_index=False,timeout=30)
                df=normalise(df)
                fn=out/f'{ticker}_{mode}_{stamp}.csv'
                df.to_csv(fn,index=True,encoding='utf-8-sig',float_format='%.17g',date_format='%Y-%m-%d')
                # Analysis uses the persisted artifact, not a hidden in-memory variant.
                stored=pd.read_csv(fn,index_col='Date',parse_dates=['Date'],float_precision='round_trip')
                data[repaired]=stored
                record.update(file=fn.name,sha256=sha(fn),rows=len(stored),status='OK')
            except Exception as e:
                errs.append(f'{mode}: {type(e).__name__}: {e}')
                record.update(status='FEHLER',error=errs[-1])
            record['finished_utc']=datetime.now(timezone.utc).isoformat()
            manifest['downloads'].append(record)
            (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
            time.sleep(2)
        if len(data)!=2:
            summaries.append(dict(Aktie=ticker,Status='DOWNLOAD FEHLER',Fehler=' | '.join(errs),Datenunterschiede=None,Kipps=None,Vergleichbare_Tage=0));continue
        a,b=data[False],data[True]
        # Persist all per-day decisions even if comparison later fails validation.
        for flag,df in data.items():
            if 'Close' in df:
                decisions=decision(df).reset_index()
                write_csv(decisions,out/f'{ticker}_entscheidungen_repair_{str(flag).lower()}.csv')
        differences=field_diffs(a,b,ticker)
        write_csv(pd.DataFrame(differences,columns=['Aktie','Datum','Feld','Original','Repariert']),out/f'{ticker}_datenunterschiede.csv')
        alld.extend(differences)
        try:
            r=analyse(a,b,ticker);allf.extend(r['flips'])
            allp.extend([dict(Aktie=ticker,**x) for x in r['positions']])
            summaries.append(dict(Aktie=ticker,Status=r['status'],Datenunterschiede=len(differences),
                Kipps=len(r['flips']) if r['status']=='OK' else None,Vergleichbare_Tage=r['comparable']))
        except Exception as e:
            summaries.append(dict(Aktie=ticker,Status='BLOCKIERT: '+str(e),Datenunterschiede=len(differences),Kipps=None,Vergleichbare_Tage=0))
    sd=pd.DataFrame(summaries)
    fc=['Aktie','Datum','Original','Repariert','Einordnung','Erste_Kippentscheidung','Kategorie',
        'Ursache_Datum','Feld','Alter_Wert','Neuer_Wert','Einzel_Ruecktausch_Treffer','Weitere_Treffer','Kandidaten','Auch_vorwaerts_ausreichend']
    fd=pd.DataFrame(allf).reindex(columns=fc)
    dd=pd.DataFrame(alld,columns=['Aktie','Datum','Feld','Original','Repariert'])
    pd_=pd.DataFrame(allp,columns=['Aktie','Datum','Original_Position','Repariert_Position','Typ'])
    for name,frame in [('zusammenfassung',sd),('kipp_liste',fd),('datenunterschiede',dd),('positionsfolgen_NUR_ILLUSTRATION',pd_)]:
        write_csv(frame,out/(name+'.csv'))
    good=sd[sd.Status=='OK']; bad=len(sd)-len(good)
    nchanges=int((pd.to_numeric(sd.Datenunterschiede,errors='coerce')>0).sum())
    nflip=len(fd)
    leaders='Keine Aktie mit Kipp' if nflip==0 else ', '.join(fd.groupby('Aktie').size().loc[lambda s:s==s.max()].index)
    text=f'Vorgesehen: 30 Aktien. Vollstaendig vergleichbar: {len(good)}. Fehler/blockiert: {bad}. Aktien mit erfassten Datenunterschieden: {nchanges}. Direkte Entscheidungs-Kipps: {nflip}. Meiste Kipps: {leaders}.'
    status='UNVOLLSTAENDIG' if bad else 'VOLLSTAENDIG'
    sections=['<meta charset="utf-8"><style>body{font-family:Arial;max-width:1400px;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #aaa;padding:5px}h1{color:#17445a}</style>',
        '<h1>Kipp-Bericht: '+status+'</h1>','<p>'+html.escape(text)+'</p>',
        '<h2>Grenzen</h2><p>'+html.escape(WARNING)+'</p>',
        '<p>Beobachtete Signalunterschiede sind keine ausgefuehrten Trades. Kein Renditebeweis. '
        'Keine Positionsfolgen in der Kipp-Zaeh lung. Der separate Long/Flat-Zustand ist nur eine Illustration. '
        'Fehlende Tage oder ungueltige Schlusskurse blockieren die Kausalzuordnung fuer die ganze Aktie. '
        'Kein Auffuellen, keine Datumsverschiebung. Keine Daten vor 2020: die ersten 50 Beobachtungen sind Aufwaermphase. '
        'Alle unterschiedlichen Entscheidungen sind direkte Unterschiede dieser zustandslosen Signalregel, '
        'nicht automatisch Folgen eines frueheren Trades. Die Kategorie mehrere Aenderungen ist ein Einzel-Ruecktausch-Befund, '
        'kein Beweis einer kleinsten gemeinsamen Ursachenmenge. Ein wiederherstellender Wert ist nicht zwingend alleinige Ursache.</p>',
        '<h2>Aktien</h2>',sd.to_html(index=False,escape=True),'<h2>Alle Kipp-Entscheidungen</h2>',fd.to_html(index=False,escape=True),
        '<h2>10 kuenstliche Tests</h2>',pd.read_csv(out/'tests/tests.csv').to_html(index=False,escape=True)]
    (out/'bericht.html').write_text('\n'.join(sections),encoding='utf-8')
    (out/'ERGEBNIS.txt').write_text(text+'\n\n'+WARNING,encoding='utf-8')
    manifest['result']=dict(complete=(bad==0),comparable_tickers=len(good),blocked_or_failed=bad,flips=nflip)
    manifest['files']={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.name!='manifest.json'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')
    print(text);print('Bericht:',out/'bericht.html')
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--tests-only',action='store_true');p.add_argument('--out',default='ergebnisse');args=p.parse_args()
    root=Path(args.out)
    if args.tests_only: tests(root/'tests')
    else: run(root)
if __name__=='__main__':main()
