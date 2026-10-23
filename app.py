import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone

st.set_page_config(page_title='AI Global Portfolio Manager', page_icon='🌍', layout='wide')
st.title('🌍 AI Global Portfolio Manager')
st.caption('v0.3 · Análisis cuantitativo experimental · Datos de terceros potencialmente retrasados · SIN órdenes reales')
st.warning('SIMULACIÓN. Las puntuaciones son reglas cuantitativas, no decisiones de una IA autónoma ni recomendaciones personalizadas. No existe conexión a un broker.')

UNIVERSE = {
 'SPY':'ETF EE.UU.', 'QQQ':'ETF tecnología EE.UU.', 'VXUS':'ETF internacional', 'BABA':'China (ADR)',
 'JD':'China (ADR)', 'PDD':'China (ADR)', 'TSM':'Taiwán (ADR)', 'ASML':'Países Bajos',
 'MSFT':'EE.UU.', 'NVDA':'EE.UU.', 'GOOGL':'EE.UU.', 'AMZN':'EE.UU.',
 'MELI':'Latinoamérica', 'NVO':'Dinamarca (ADR)', 'TM':'Japón (ADR)', 'INFY':'India (ADR)',
 'EWJ':'ETF Japón', 'EWZ':'ETF Brasil', 'INDA':'ETF India', 'FXI':'ETF China'
}

@st.cache_data(ttl=3600, show_spinner=False)
def load_prices(symbols):
    results = {}
    errors = []
    for ticker in symbols:
        try:
            hist = yf.Ticker(ticker).history(period='1y', interval='1d', auto_adjust=True)
            if hist.empty or len(hist) < 130:
                errors.append(ticker)
                continue
            series = hist['Close'].dropna()
            if len(series) < 130 or float(series.iloc[-1]) <= 0:
                errors.append(ticker)
                continue
            results[ticker] = series
        except Exception:
            errors.append(ticker)
    return results, errors

def compute_ranking(series_map):
    rows = []
    for ticker, prices in series_map.items():
        returns = prices.pct_change().dropna()
        if len(returns) < 120:
            continue
        momentum_3m = float(prices.iloc[-1] / prices.iloc[-64] - 1)
        momentum_6m = float(prices.iloc[-1] / prices.iloc[-127] - 1)
        vol = float(returns.tail(63).std() * np.sqrt(252))
        if not np.isfinite(vol) or vol <= 0:
            continue
        rows.append({'Símbolo':ticker,'Mercado':UNIVERSE[ticker], 'Precio USD aprox.':round(float(prices.iloc[-1]),2),
                     'Momentum 3m %':round(100*momentum_3m,2), 'Momentum 6m %':round(100*momentum_6m,2),
                     'Volatilidad anual %':round(100*vol,2), '_mom':0.5*momentum_3m+0.5*momentum_6m, '_vol':vol,
                     'Última fecha':str(prices.index[-1].date())})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # Cross-sectional percentile ranks: higher momentum and lower volatility preferred.
    df['Puntuación'] = (100*(0.75*df['_mom'].rank(pct=True)+0.25*(1-df['_vol'].rank(pct=True)))).round(1)
    return df.sort_values('Puntuación',ascending=False).reset_index(drop=True)

with st.sidebar:
    st.header('Parámetros de simulación')
    capital = st.number_input('Capital simulado (USD)', min_value=100.0, value=5000.0, step=500.0)
    max_positions = st.slider('Número máximo de posiciones', 2, 10, 6)
    max_weight = st.slider('Máximo por instrumento (%)', 5, 30, 20, 5)
    cash_floor = st.slider('Efectivo mínimo (%)', 10, 70, 20, 5)
    st.caption('Estos controles modifican una propuesta hipotética; no ejecutan operaciones.')

st.subheader('Datos de mercado')
if st.button('Actualizar datos (caché de hasta 1 hora)'):
    load_prices.clear()
with st.spinner('Consultando precios históricos...'):
    prices, failures = load_prices(tuple(UNIVERSE.keys()))

if failures:
    st.info('Sin datos suficientes para: '+', '.join(failures)+'. No se sustituyen por precios inventados.')
if not prices:
    st.error('No se pudieron obtener cotizaciones. Intenta nuevamente más tarde; el proveedor puede limitar solicitudes.')
    st.stop()
ranking = compute_ranking(prices)
if ranking.empty:
    st.error('No hay suficientes datos válidos para generar el ranking.')
    st.stop()

c1,c2,c3 = st.columns(3)
c1.metric('Capital simulado',f'US${capital:,.0f}')
c2.metric('Instrumentos analizados',str(len(ranking)))
c3.metric('Fecha más reciente',max(ranking['Última fecha']))
st.caption('Precios de Yahoo Finance mediante yfinance; pueden ser retrasados, ajustados o incompletos. No son cotizaciones ejecutables.')
st.subheader('Ranking cuantitativo')
st.dataframe(ranking.drop(columns=['_mom','_vol']), hide_index=True, use_container_width=True)
st.caption('Puntuación: 75% ranking relativo de momentum a 3/6 meses y 25% menor volatilidad a 3 meses. No incorpora balances, valoración, noticias ni riesgos regulatorios.')

st.subheader('Propuesta de cartera simulada')
# Invest only in instruments with positive momentum; cap each weight and preserve cash.
eligible = ranking[(ranking['Momentum 3m %']>0)&(ranking['Momentum 6m %']>0)].head(max_positions)
investable_pct = max(0,100-cash_floor)
per_position = min(float(max_weight),investable_pct/max(len(eligible),1))
proposal = pd.DataFrame([{'Símbolo':r['Símbolo'],'Peso %':round(per_position,2),'Monto USD':round(capital*per_position/100,2), 'Motivo':'Momentum 3m y 6m positivo; puntuación relativa'} for _,r in eligible.iterrows()])
allocated = float(proposal['Monto USD'].sum()) if not proposal.empty else 0.0
cash = round(float(capital)-allocated,2)
proposal = pd.concat([proposal,pd.DataFrame([{'Símbolo':'EFECTIVO','Peso %':round(100*cash/capital,2),'Monto USD':cash,'Motivo':'Reserva / sin señales suficientes'}])],ignore_index=True)
st.dataframe(proposal,hide_index=True,use_container_width=True)
st.bar_chart(proposal.set_index('Símbolo')['Monto USD'])
st.caption('La cartera es una asignación teórica calculada hoy. No es una cartera ejecutada; no hay P&L, backtest, costos, ni historial persistente. Las acciones pueden estar denominadas o negociarse de forma distinta según mercado.')
st.subheader('Estado técnico')
st.write('🟢 Dashboard · 🟢 Datos históricos consultables · 🟢 Ranking basado en reglas · 🟡 Backtesting pendiente · 🔴 Ejecución programada pendiente · 🔴 Broker desconectado')
st.caption('No compartas claves API en el repositorio público. Datos solo para investigación y pruebas.')
