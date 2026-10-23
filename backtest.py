"""Educational monthly walk-forward simulation. No brokerage connections."""
import numpy as np
import pandas as pd


def simulate(price_map, capital=5000.0, positions=6, max_weight=0.20, cash_floor=0.20, cost_bps=10):
    # Intersection prevents accidental forward-filling missing securities' prices.
    panel = pd.concat({k: v.tz_localize(None) if v.index.tz is not None else v for k,v in price_map.items()},axis=1).sort_index()
    panel = panel.ffill(limit=3).dropna(axis=0,how='any')
    if len(panel) < 190 or len(panel.columns) < 3:
        raise ValueError('Se necesitan al menos 190 sesiones comunes y 3 instrumentos con datos completos.')
    # Signals at close t, orders at close t+1 (no lookahead). Portfolio returns start t+2.
    dates = panel.index
    rebal = set()
    for i in range(127,len(dates)-2):
        if dates[i].month != dates[i+1].month:
            rebal.add(i)
    weights = pd.Series(0.0,index=panel.columns)
    equity = float(capital)
    cash_weight = 1.0
    records=[]; trades=[]
    returns = panel.pct_change().fillna(0)
    benchmark = float(capital)
    for i in range(128,len(panel)):
        # weights determined after prior close; earn today's returns first.
        daily = float((weights * returns.iloc[i]).sum())
        equity *= (1+daily)
        benchmark *= (1+float(returns['SPY'].iloc[i])) if 'SPY' in panel.columns else 1.0
        if i-1 in rebal:
            s = panel.iloc[i-1]
            m3 = s / panel.iloc[i-1-63] - 1
            m6 = s / panel.iloc[i-1-126] - 1
            vol = returns.iloc[i-1-62:i].std()*np.sqrt(252)
            score = 0.75*((m3+m6)/2).rank(pct=True)+0.25*(1-vol.rank(pct=True))
            eligible = score[(m3>0)&(m6>0)&(vol>0)].sort_values(ascending=False).head(positions)
            target = pd.Series(0.0,index=panel.columns)
            if len(eligible):
                each = min(float(max_weight),(1-float(cash_floor))/len(eligible))
                target.loc[eligible.index]=each
            # approximate turnover costs; no claim of executable fill prices
            turnover = float((target-weights).abs().sum())
            fee = equity*turnover*cost_bps/10000
            equity -= fee
            trades.append({'Fecha':str(dates[i].date()),'Rotación %':round(turnover*100,2),'Costo simulado USD':round(fee,2),'Activos':', '.join(eligible.index)})
            weights = target
            cash_weight = 1-float(weights.sum())
        records.append({'Fecha':dates[i], 'Estrategia':equity,'SPY (referencia)':benchmark,'Efectivo %':cash_weight*100})
    result = pd.DataFrame(records).set_index('Fecha')
    result['Drawdown %']=(result['Estrategia']/result['Estrategia'].cummax()-1)*100
    return result,pd.DataFrame(trades)
