"""Long-only, monthly close-signal/next-session execution, 12-month evaluation.
Educational proxy factors only; NO point-in-time fundamental/analyst/13F history.
"""
import numpy as np
import pandas as pd

MODELS = {
    'Momentum actual': 'Momentum 3/6 meses (75%) + volatilidad inversa (25%)',
    'Calidad–valor–momentum (proxy)': 'Momentum + estabilidad de retornos + reversión de 12 meses (NO fundamentales)',
    'Rentabilidad–valoración (proxy)': 'Estabilidad + reversión de 12 meses (NO utilidades ni múltiplos)',
    'Multifactor cuantitativo (proxy)': 'Momentum + estabilidad + reversión + menor volatilidad (NO analistas/13F históricos)',
}

def _pct(s, higher=True):
    v = s.rank(pct=True)
    return v if higher else (1-v)

def signals(prices, end):
    h = prices.iloc[:end+1]
    if len(h) < 254:
        return None
    p = h.iloc[-1]
    r = h.pct_change(fill_method=None)
    mom3 = p / h.iloc[-64] - 1
    mom6 = p / h.iloc[-127] - 1
    mom12 = p / h.iloc[-253] - 1
    vol = r.iloc[-63:].std() * np.sqrt(252)
    stability = r.iloc[-126:].mean() / r.iloc[-126:].std().replace(0,np.nan)
    valid = (p > 0) & vol.gt(0) & mom3.notna() & mom6.notna() & mom12.notna()
    scores = {
        'Momentum actual': .75*_pct((mom3+mom6)/2)+.25*_pct(vol,False),
        'Calidad–valor–momentum (proxy)': .4*_pct((mom3+mom6)/2)+.35*_pct(stability)+.25*_pct(-mom12),
        'Rentabilidad–valoración (proxy)': .55*_pct(stability)+.45*_pct(-mom12),
        'Multifactor cuantitativo (proxy)': .35*_pct((mom3+mom6)/2)+.25*_pct(stability)+.20*_pct(-mom12)+.20*_pct(vol,False),
    }
    return {k:v.where(valid & mom3.gt(0) & mom6.gt(0)).dropna().sort_values(ascending=False) for k,v in scores.items()}

def simulate_models(price_map, capital=5000., positions=6, max_weight=.20, cash_floor=.20, cost_bps=10, months=12):
    if 'SPY' not in price_map:
        raise ValueError('Se necesita SPY para el benchmark.')
    panel = pd.concat({k: s.rename(k) for k,s in price_map.items()},axis=1).sort_index()
    panel.index = pd.to_datetime(panel.index).tz_localize(None) if panel.index.tz is not None else pd.to_datetime(panel.index)
    panel = panel.ffill(limit=3)
    panel = panel.dropna(axis=1, thresh=int(len(panel)*.95))
    panel = panel.dropna(axis=0,how='any')
    if len(panel)< 260+int(months*18) or 'SPY' not in panel.columns:
        raise ValueError('Historial insuficiente para 12 meses de evaluación y 12 meses de indicadores. Descarga al menos 3 años.')
    start_date = panel.index[-1]-pd.DateOffset(months=months)
    start = int(panel.index.searchsorted(start_date))
    if start < 254: raise ValueError('Falta historial de formación de señales previo a la evaluación.')
    ret = panel.pct_change(fill_method=None).fillna(0)
    names=list(MODELS)
    weights={n:pd.Series(0.,index=panel.columns) for n in names}
    wealth={n:float(capital) for n in names}
    wealth['SPY']=float(capital)
    rows=[]; trades=[]
    # At start: choose from prior close and pay turnover cost at first evaluation close.
    for i in range(start,len(panel)):
        if i>start:
            for n in names:
                old=weights[n]
                wealth[n]*=1+float((old*ret.iloc[i]).sum())
                # Let weights drift after returns, before the next rebalance.
                gross=1+float((old*ret.iloc[i]).sum())
                if gross>0: weights[n]=old*(1+ret.iloc[i])/gross
            wealth['SPY']*=1+float(ret['SPY'].iloc[i])
        is_rebalance=(i==start or panel.index[i].month!=panel.index[i-1].month)
        if is_rebalance:
            sig=signals(panel,i-1)
            for n in names:
                eligible=sig[n].head(positions).index if sig else []
                target=pd.Series(0.,index=panel.columns)
                if len(eligible): target.loc[eligible]=min(max_weight,(1-cash_floor)/len(eligible))
                turnover=float((target-weights[n]).abs().sum())
                fee=wealth[n]*turnover*cost_bps/10000
                wealth[n]-=fee
                weights[n]=target
                trades.append({'Fecha':panel.index[i].date().isoformat(),'Modelo':n,'Rotación %':round(turnover*100,2),'Costo USD':round(fee,2),'Instrumentos':', '.join(eligible)})
        rows.append({'Fecha':panel.index[i],**wealth})
    result=pd.DataFrame(rows).set_index('Fecha')
    return result,pd.DataFrame(trades)

def metrics(series, capital):
    returns=series.pct_change().dropna()
    total=float(series.iloc[-1]/capital-1)
    dd=float((series/series.cummax()-1).min())
    vol=float(returns.std()*np.sqrt(252)) if len(returns)>2 else np.nan
    sharpe=float(returns.mean()/returns.std()*np.sqrt(252)) if len(returns)>2 and returns.std()>0 else np.nan
    return {'Retorno %':round(total*100,2),'Drawdown %':round(dd*100,2),'Volatilidad %':round(vol*100,2),'Sharpe (rf=0)':round(sharpe,2)}
    print("BACKTEST V0.5 CARGADO", list(MODELS.keys()))
