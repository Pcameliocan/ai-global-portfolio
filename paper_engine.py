"""Deterministic, long-only paper ledger. No broker, credentials or order routing."""
from __future__ import annotations
from datetime import date
import math

FEE_RATE = 0.001  # 10 bps on executed notional
MIN_TRADE_USD = 25.0
EPS = 1e-8


def fresh_date(value: str, today: date, max_days: int = 4) -> bool:
    try:
        age = (today - date.fromisoformat(value)).days
        return 0 <= age <= max_days
    except (ValueError, TypeError):
        return False


def value_portfolio(cash, holdings, prices):
    return round(float(cash) + sum(float(qty) * float(prices[t]) for t, qty in holdings.items()), 4)


def fill_pending(state, prices, market_date, min_cash_pct=.20):
    """Execute previous market-day target at today's observed adjusted close.

    This is a delayed-close *research fill*, not a tradable live fill. Never
    execute a target created on the same market date. Missing quotes => fail
    closed; no partial batch.
    """
    pending = state.get('pending')
    cash = float(state['cash'])
    holdings = {k: float(v) for k, v in state.get('holdings', {}).items() if float(v) > EPS}
    if not pending or pending['signal_date'] >= market_date:
        return cash, holdings, [], pending
    targets = {str(k): float(v) for k, v in pending['weights'].items()}
    if any(not math.isfinite(w) or w < 0 or w > .20 + EPS for w in targets.values()):
        raise ValueError('Target weights outside per-instrument risk cap')
    if sum(targets.values()) > 1-min_cash_pct+EPS:
        raise ValueError('Target weights violate cash floor')
    symbols = set(holdings) | set(targets)
    if any(t not in prices or not math.isfinite(float(prices[t])) or float(prices[t]) <= 0 for t in symbols):
        raise ValueError('Missing or invalid execution price; aborting entire batch')
    equity = value_portfolio(cash, holdings, prices)
    trades = []
    # Sell first; sell proceeds may fund buys. Fees charged both directions.
    for ticker in sorted(symbols):
        current = holdings.get(ticker, 0.0)
        target_qty = equity * targets.get(ticker, 0.0) / prices[ticker]
        sell_qty = max(0.0, current - target_qty)
        notional = sell_qty * prices[ticker]
        if notional < MIN_TRADE_USD: continue
        cash += notional * (1-FEE_RATE)
        holdings[ticker] = max(0.0, current-sell_qty)
        trades.append({'ticker':ticker,'side':'SELL','quantity':round(sell_qty,8),'price':round(prices[ticker],6),'fee':round(notional*FEE_RATE,6),'notional':round(notional,6)})
    # Scale buy requests to available cash above cash floor, including fees.
    min_cash = equity * min_cash_pct
    requests=[]
    for ticker in sorted(targets):
        desired = equity * targets[ticker]
        current = holdings.get(ticker, 0.0) * prices[ticker]
        delta = desired-current
        if delta >= MIN_TRADE_USD: requests.append((ticker, delta))
    available = max(0.0, cash-min_cash)
    total_cost = sum(v*(1+FEE_RATE) for _,v in requests)
    scale = min(1.0, available/total_cost) if total_cost else 0.0
    for ticker, requested in requests:
        notional = requested*scale
        if notional < MIN_TRADE_USD: continue
        fee = notional*FEE_RATE
        if cash-notional-fee < min_cash-0.0001:
            notional = max(0.0, (cash-min_cash)/(1+FEE_RATE))
            fee = notional*FEE_RATE
        if notional < MIN_TRADE_USD: continue
        qty = notional/prices[ticker]
        cash -= notional+fee
        holdings[ticker] = holdings.get(ticker,0.0)+qty
        trades.append({'ticker':ticker,'side':'BUY','quantity':round(qty,8),'price':round(prices[ticker],6),'fee':round(fee,6),'notional':round(notional,6)})
    holdings = {k:round(v,8) for k,v in holdings.items() if v>EPS}
    if cash < min_cash - 0.01:
        raise ValueError('Cash floor breached')
    return round(cash,6), holdings, trades, None


def target_weights(allocations):
    result={}
    for a in allocations:
        ticker=a['Símbolo']
        result[ticker]=float(a['Peso %'])/100
    return result
