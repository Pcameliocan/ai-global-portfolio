"""v0.8: conservative thematic exposure, turnover-aware replacement and data audits.
All allocations are hypothetical and never execute orders.
"""
import math
import pandas as pd

THEMES = {
    'MSFT': 'IA/infraestructura digital', 'NVDA': 'IA/infraestructura digital',
    'GOOGL': 'IA/infraestructura digital', 'AMZN': 'IA/infraestructura digital',
    'TSM': 'IA/infraestructura digital', 'ASML': 'IA/infraestructura digital',
    'QQQ': 'IA/infraestructura digital', 'INFY': 'IA/infraestructura digital',
    'BABA': 'Comercio digital', 'JD': 'Comercio digital', 'PDD': 'Comercio digital',
    'MELI': 'Comercio digital', 'JPM': 'Finanzas', 'BRK-B': 'Finanzas',
    'UNH': 'Salud', 'JNJ': 'Salud', 'ABBV': 'Salud', 'NVO': 'Salud',
    'XOM': 'Energía', 'CVX': 'Energía', 'CAT': 'Industria', 'DE': 'Industria',
    'NEE': 'Servicios públicos', 'COST': 'Consumo', 'PG': 'Consumo', 'KO': 'Consumo',
    'TM': 'Industria', 'SPY': 'ETF amplio', 'VXUS': 'ETF amplio',
    'EWJ': 'ETF regional', 'EWZ': 'ETF regional', 'INDA': 'ETF regional',
    'FXI': 'ETF regional', 'XLV': 'ETF sectorial', 'XLF': 'ETF sectorial',
    'XLE': 'ETF sectorial', 'XLI': 'ETF sectorial',
}

def confidence(coverage):
    if pd.isna(coverage): return 'Sin datos'
    return 'Alta' if coverage >= 85 else 'Media' if coverage >= 65 else 'Insuficiente'

def allocate_with_theme(rows, capital, max_positions, max_weight, cash_floor,
                        minimum_score, minimum_coverage, sector_cap, sector_map,
                        theme_cap=.30, current_positions=None, replacement_margin=7):
    """Greedy conservative allocation. Current positions are optional simulated tickers.
    Replacement margin is an absolute score difference, not an expected return.
    """
    current_positions=set(current_positions or [])
    eligible=[]
    for r in rows:
        try:
            score=float(r.get('score'));cov=float(r.get('coverage'))
        except (ValueError,TypeError): continue
        if not math.isfinite(score) or not math.isfinite(cov): continue
        if score < minimum_score or cov < minimum_coverage or not r.get('ticker'): continue
        eligible.append(r)
    eligible.sort(key=lambda r:(-float(r['score']),str(r['ticker'])))
    # Do not replace a held name for a marginal score improvement.
    if current_positions:
        held_scores=[float(r['score']) for r in eligible if r['ticker'] in current_positions]
        threshold=min(held_scores) if held_scores else None
        if threshold is not None:
            eligible=[r for r in eligible if r['ticker'] in current_positions or float(r['score']) >= threshold + replacement_margin]
            eligible.sort(key=lambda r:(r['ticker'] not in current_positions,-float(r['score']),str(r['ticker'])))
    remaining=max(0.,1-float(cash_floor));alloc=[];sector_used={};theme_used={}
    for r in eligible:
        if len(alloc)>=max_positions or remaining < .005: break
        t=str(r['ticker']); sector=sector_map.get(t,'Sin clasificar');theme=THEMES.get(t,'Sin clasificar')
        w=min(float(max_weight),remaining,max(0.,sector_cap-sector_used.get(sector,0.)),
              max(0.,theme_cap-theme_used.get(theme,0.)))
        if w < .005: continue
        sector_used[sector]=sector_used.get(sector,0.)+w
        theme_used[theme]=theme_used.get(theme,0.)+w
        remaining-=w
        alloc.append({'Símbolo':t,'Sector / exposición':sector,'Tema de riesgo':theme,
                      'Score':float(r['score']),'Cobertura %':float(r['coverage']),
                      'Confianza':confidence(float(r['coverage'])),
                      'Peso %':round(100*w,2),'Monto USD':round(capital*w,2),
                      'Decisión':'Mantener (simulado)' if t in current_positions else 'Candidato simulado'})
    cash=round(capital-sum(x['Monto USD'] for x in alloc),2)
    return alloc,cash

def benchmark_cash_curve(spy_curve, initial_capital, cash_weight=.20):
    """Buy-and-hold SPY/cash from first simulated date; zero cash interest, no fees."""
    return initial_capital*(cash_weight+(1-cash_weight)*spy_curve/float(spy_curve.iloc[0]))
