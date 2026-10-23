"""Current-snapshot scoring only. Never use these scores in historical backtests."""
import math
import pandas as pd
import numpy as np

RATINGS={'strong_buy':100,'strong buy':100,'buy':75,'hold':50,'sell':25,'strong_sell':0,'strong sell':0}
WEIGHTS={'Momentum':.35,'Calidad':.25,'Valoración':.15,'Analistas':.15,'Institucionales':.10}

def _number(v):
    try:
        f=float(v)
        return f if math.isfinite(f) else None
    except (ValueError,TypeError): return None

def _linear(v,low,high,reverse=False):
    v=_number(v)
    if v is None: return None
    result=float(np.clip(100*(v-low)/(high-low),0,100))
    return 100-result if reverse else result

def _average(values):
    vals=[v for v in values if v is not None]
    return round(float(np.mean(vals)),1) if vals else None

def calculate_score(prices,info,institutional=None):
    """Missing data is explicitly excluded and coverage is reported."""
    s=pd.Series(prices).dropna().astype(float)
    momentum=None
    if len(s)>=127 and s.iloc[-127]>0:
        r3=(s.iloc[-1]/s.iloc[-64]-1) if len(s)>=64 else None
        r6=s.iloc[-1]/s.iloc[-127]-1
        momentum=_average([_linear(r3,-.20,.30),_linear(r6,-.30,.50)])
    quality=_average([_linear(info.get('returnOnEquity'),0,.35),_linear(info.get('revenueGrowth'),-.10,.35),_linear(info.get('profitMargins'),-.05,.30),_linear(info.get('debtToEquity'),0,250,True)])
    pe=_number(info.get('forwardPE'))
    valuation=_average([_linear(pe,8,50,True) if pe is not None and pe>0 else None, _linear(info.get('priceToBook'),1,12,True)])
    rating=str(info.get('recommendationKey') or '').lower().replace('-','_')
    analyst=RATINGS.get(rating)
    inst=_number(institutional) # Not inferred from institutionalPercentHeld: not a buy/sell signal
    factors={'Momentum':momentum,'Calidad':quality,'Valoración':valuation,'Analistas':analyst,'Institucionales':inst}
    coverage=sum(WEIGHTS[k] for k,v in factors.items() if v is not None)
    score=round(sum(WEIGHTS[k]*v for k,v in factors.items() if v is not None)/coverage,1) if coverage else None
    return {'score':score,'coverage':round(coverage*100,1),'factors':factors}

def propose_allocation(rows,capital=5000,max_positions=6,max_weight=.20,cash_floor=.20,minimum_score=65,minimum_coverage=65):
    """Non-executable target weights. Caps total investment and individual exposure."""
    eligible=[r for r in rows if r.get('score') is not None and r['score']>=minimum_score and r['coverage']>=minimum_coverage]
    eligible=sorted(eligible,key=lambda r:r['score'],reverse=True)[:max_positions]
    investable=max(0,1-cash_floor)
    remaining=investable
    allocations=[]
    for r in eligible:
        w=min(max_weight,remaining)
        if w<=1e-9: break
        allocations.append({'Símbolo':r['ticker'],'Score':r['score'],'Cobertura %':r['coverage'],'Peso %':round(w*100,2),'Monto USD':round(w*capital,2),'Decisión':'Candidato simulado'})
        remaining-=w
    cash=round(capital*(1-sum(x['Peso %'] for x in allocations)/100),2)
    return allocations,cash
