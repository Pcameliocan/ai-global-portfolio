"""Daily autonomous *paper-only* evaluator; NEVER routes live orders."""
import os
from datetime import datetime, timezone
import math
import pandas as pd
import yfinance as yf
from hybrid import calculate_score
from risk_v08 import allocate_with_theme
from paper_engine import fill_pending, target_weights, value_portfolio, fresh_date
from supabase_store import Store
from portfolio_config import UNIVERSE, SECTORS

INITIAL_CAPITAL=5000.0
MAX_WEIGHT=.20
CASH_FLOOR=.20
SECTOR_CAP=.30
THEME_CAP=.30
MAX_POSITIONS=6
MIN_SCORE=65
MIN_COVERAGE=65


def load_market():
    """Use completed US session SPY close as the common market date."""
    spy=yf.Ticker('SPY').history(period='10d',interval='1d',auto_adjust=True)['Close'].dropna()
    if spy.empty: raise RuntimeError('SPY quote unavailable; no changes committed')
    market_date=spy.index[-1].date().isoformat()
    if not fresh_date(market_date,datetime.now(timezone.utc).date(),max_days=4):
        raise RuntimeError('SPY market date is stale; no changes committed')
    series={}; excluded={}
    for ticker in UNIVERSE:
        try:
            s=yf.Ticker(ticker).history(period='1y',interval='1d',auto_adjust=True)['Close'].dropna()
            if len(s)<127: excluded[ticker]='less than 127 observations';continue
            if s.index[-1].date().isoformat()!=market_date:
                excluded[ticker]='quote date differs from SPY';continue
            series[ticker]=s
        except Exception as exc:
            excluded[ticker]=f'data retrieval error: {type(exc).__name__}'
    if 'SPY' not in series: raise RuntimeError('SPY has no eligible series')
    return market_date,series,excluded


def main():
    store=Store(os.environ['SUPABASE_URL'],os.environ['SUPABASE_SERVICE_ROLE_KEY'])
    state=store.state()
    market_date, series, excluded=load_market()
    if store.request('GET',f'paper_runs?market_date=eq.{market_date}&select=market_date'):
        print('Already processed market date:',market_date);return
    # All held symbols must have a fresh quote; fail closed rather than invent values.
    held=set(state['holdings'])
    pending=state.get('pending') or {}
    needed=held | set(pending.get('weights',{}))
    if any(t not in series for t in needed):
        raise RuntimeError(f'Missing same-date quotes for held/pending symbols: {sorted(needed-set(series))}')
    prices={ticker:float(s.iloc[-1]) for ticker,s in series.items()}
    cash,holdings,trades,_=fill_pending(state,prices,market_date,CASH_FLOOR)
    equity=value_portfolio(cash,holdings,prices)
    if not math.isfinite(equity) or equity<=0: raise RuntimeError('Invalid equity')
    ranking=[]
    for ticker,s in series.items():
        try:
            info=yf.Ticker(ticker).info or {}
            result=calculate_score(s,info,institutional=None)
            ranking.append({'ticker':ticker,'score':result['score'],
                            'coverage':result['coverage'],'factors':result['factors']})
        except Exception as exc:
            excluded[ticker]=f'factor error: {type(exc).__name__}'
    ranking.sort(key=lambda x: (x['score'] is None,-(x['score'] or 0),x['ticker']))
    allocations,_=allocate_with_theme(ranking,equity,MAX_POSITIONS,MAX_WEIGHT,
        CASH_FLOOR,MIN_SCORE,MIN_COVERAGE,SECTOR_CAP,SECTORS,theme_cap=THEME_CAP,
        current_positions=list(holdings),replacement_margin=7)
    target=target_weights(allocations)
    # Prevent involuntary liquidation of holdings due to missing factor data.
    # Keep current weights if an existing holding has no usable score today.
    scored={r['ticker'] for r in ranking if r['score'] is not None}
    if any(t not in scored for t in holdings):
        raise RuntimeError('Missing factor data for a held symbol; no changes committed')
    new_pending={'signal_date':market_date,'weights':target,
                 'reason':'Current hybrid score, confidence, sector and thematic limits'}
    rationale=(f'{len(series)} symbols with same-day prices; {len(excluded)} excluded; '
               f'{len(allocations)} target positions; {len(trades)} paper fills from prior signal. '
               'No historical 13F input; analyst data is current snapshot. '
               'Fills use next observed close (not an executable live price).')
    result=store.commit(state['version'],market_date,cash,holdings,new_pending,
                        equity,prices['SPY'],ranking[:50],trades,rationale)
    print(result)

if __name__=='__main__': main()
