"""Optional point-in-time 13F snapshots supplied by the user. No live 13F scraping."""
import pandas as pd
import numpy as np

REQUIRED={'ticker','manager','report_date','filing_date','shares','previous_shares'}

def score_13f(data,as_of=None):
    if not REQUIRED.issubset(data.columns):
        raise ValueError('Faltan columnas: '+', '.join(sorted(REQUIRED-set(data.columns))))
    d=data.copy()
    for c in ('report_date','filing_date'):
        d[c]=pd.to_datetime(d[c],errors='coerce',utc=True)
    d['shares']=pd.to_numeric(d['shares'],errors='coerce')
    d['previous_shares']=pd.to_numeric(d['previous_shares'],errors='coerce')
    now=pd.Timestamp.now(tz='UTC') if as_of is None else pd.Timestamp(as_of)
    if now.tzinfo is None: now=now.tz_localize('UTC')
    # Exclude future/unpublished or stale data; require valid prior holding amounts.
    d=d[(d.filing_date<=now)&(d.report_date<=d.filing_date)&(d.filing_date>=now-pd.Timedelta(days=180))&(d.shares>=0)&(d.previous_shares>=0)]
    d=d.dropna(subset=['ticker','manager','report_date','filing_date','shares','previous_shares'])
    d=d.sort_values('filing_date').drop_duplicates(['ticker','manager'],keep='last')
    if d.empty: return pd.DataFrame(columns=['ticker','Institucionales','Gestores reportados','Última presentación UTC'])
    # Direction only; a 13F change is not a trade recommendation. Baseline 50.
    delta=(d.shares-d.previous_shares)
    d['signal']=np.select([delta>0,delta<0],[75.,25.],default=50.)
    return d.groupby('ticker',as_index=False).agg(**{'Institucionales':('signal','mean'),'Gestores reportados':('manager','nunique'),'Última presentación UTC':('filing_date','max')}).assign(**{'Institucionales':lambda x:x['Institucionales'].round(1)})
