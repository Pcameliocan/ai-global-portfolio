import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from portfolio_engine import MODELS, simulate_models, metrics, signals
from hybrid import calculate_score, propose_allocation

st.set_page_config(page_title='AI Global Portfolio v0.6',page_icon='🌍',layout='wide')
st.title('🌍 AI Global Portfolio Manager')
st.caption('v0.6 · Comparador 12 meses + ranking híbrido actual · SOLO SIMULACIÓN, SIN BROKER')
st.warning('Los modelos históricos son aproximaciones cuantitativas, NO réplicas de AQR, Dimensional o BlackRock. Sin recomendaciones personalizadas ni operaciones reales.')
UNIVERSE={'SPY':'ETF EE.UU.','QQQ':'ETF Nasdaq','VXUS':'ETF internacional','BABA':'China ADR','JD':'China ADR','PDD':'China ADR','TSM':'Taiwán ADR','ASML':'Países Bajos','MSFT':'EE.UU.','NVDA':'EE.UU.','GOOGL':'EE.UU.','AMZN':'EE.UU.','MELI':'LatAm','NVO':'Dinamarca ADR','TM':'Japón ADR','INFY':'India ADR','EWJ':'ETF Japón','EWZ':'ETF Brasil','INDA':'ETF India','FXI':'ETF China'}

@st.cache_data(ttl=3600,show_spinner=False)
def load_prices():
    out={}; missing=[]
    for ticker in UNIVERSE:
        try:
            h=yf.Ticker(ticker).history(period='3y',interval='1d',auto_adjust=True)
            s=h['Close'].dropna()
            if len(s)>500: out[ticker]=s
            else: missing.append(ticker)
        except Exception: missing.append(ticker)
    return out,missing

@st.cache_data(ttl=86400,show_spinner=False)
def live_factors(ticker):
    try:
        info=yf.Ticker(ticker).info or {}
        return {'Fecha consulta (UTC)':pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d'),
            'Recomendación':str(info.get('recommendationKey') or 'Sin dato'),
            'Analistas':info.get('numberOfAnalystOpinions'),
            'Precio objetivo':info.get('targetMeanPrice'),
            'P/E forward':info.get('forwardPE'),
            'ROE':info.get('returnOnEquity'),
            'Crecimiento ingresos':info.get('revenueGrowth'),
            'Deuda / patrimonio':info.get('debtToEquity')}
    except Exception: return {}

RATING={'strong_buy':100,'strong buy':100,'buy':75,'hold':50,'sell':25,'strong_sell':0,'strong sell':0}
with st.sidebar:
    capital=st.number_input('Capital simulado USD',min_value=100.,value=5000.,step=500.)
    positions=st.slider('Máximo de posiciones',2,10,6)
    max_weight=st.slider('Máximo por instrumento %',5,30,20,5)/100
    cash_floor=st.slider('Efectivo mínimo %',10,70,20,5)/100
    st.caption('El backtest evalúa los últimos 12 meses. Descarga datos anteriores solo para construir indicadores.')
if st.button('Actualizar precios'):
    load_prices.clear()
with st.spinner('Descargando historial de precios...'):
    prices,missing=load_prices()
if missing: st.info('Sin historial suficiente: '+', '.join(missing))
if len(prices)<4 or 'SPY' not in prices:
    st.error('No hay datos suficientes del proveedor. Vuelve a intentar más tarde.'); st.stop()
st.metric('Instrumentos con historial',len(prices))
st.subheader('Comparación de cuatro estrategias · últimos 12 meses')
for k,v in MODELS.items(): st.caption(f'**{k}:** {v}')
st.caption('Las estrategias proxy usan exclusivamente precios históricos; no incorporan balances, consenso de analistas ni 13F históricos. Evitamos usar datos actuales en decisiones pasadas.')
if st.button('Ejecutar comparación histórica',type='primary'):
    try:
        with st.spinner('Simulando modelos...'):
            curve,trades=simulate_models(prices,capital,positions,max_weight,cash_floor,months=12)
        st.line_chart(curve)
        stats=pd.DataFrame([{'Modelo':k,**metrics(curve[k],capital)} for k in curve.columns])
        st.dataframe(stats,hide_index=True,use_container_width=True)
        st.caption('Señales al cierre anterior; rebalanceo al cierre siguiente (aproximación), costos 10 bps por rotación; sin spreads, impuestos ni impacto de mercado. SPY es buy-and-hold. Los pesos se ajustan diariamente por variaciones de precio. Universo fijo actual: sesgo de supervivencia/selección.')
        st.dataframe(trades,hide_index=True,use_container_width=True)
        st.download_button('Descargar curvas CSV',curve.to_csv().encode(),file_name='comparacion_v05.csv')
    except Exception as e: st.error(f'No se pudo ejecutar: {e}')
st.subheader('Señales actuales: analistas y fundamentales')
st.caption('Datos de Yahoo Finance (yfinance) con cobertura variable, potencialmente retrasados y NO históricos punto-en-tiempo. No se usan en el backtest.')
selected=st.selectbox('Examinar instrumento',list(prices.keys()))
if st.button('Consultar señales actuales'):
    d=live_factors(selected)
    if d:
        st.dataframe(pd.DataFrame([d]),hide_index=True,use_container_width=True)
        r=str(d.get('Recomendación','')).lower().replace('-','_')
        score=RATING.get(r)
        if score is not None:
            st.metric('Puntuación de recomendación (0–100)',score)
            st.caption('Conversión categórica de la recomendación agregada del proveedor; no equivale a un consenso ponderado por analista.')
        else: st.info('No hay recomendación convertible a puntuación.')
    else: st.info('Proveedor sin datos fundamentales para este instrumento.')

st.subheader('Ranking híbrido actual · v0.6')
st.caption('Puntuaciones actuales, NO backtest. Pesos: momentum 35%, calidad 25%, valoración 15%, analistas 15%, institucionales 10%. Sin fuente 13F validada, el componente institucional queda sin puntuación. El score se normaliza por factores disponibles y se informa su cobertura.')
with st.expander('Reglas de selección simulada',expanded=False):
    minimum_score=st.slider('Score mínimo',50,95,65,5)
    minimum_coverage=st.slider('Cobertura mínima de datos %',35,100,65,5)
if st.button('Calcular ranking híbrido actual',type='primary'):
    rows=[]
    progress=st.progress(0)
    for i,(ticker,series) in enumerate(prices.items()):
        try:
            info=yf.Ticker(ticker).info or {}
            result=calculate_score(series,info)
            row={'ticker':ticker,'score':result['score'],'coverage':result['coverage']}
            row.update(result['factors'])
            rows.append(row)
        except Exception as exc:
            rows.append({'ticker':ticker,'score':None,'coverage':0,'Error':str(exc)[:100]})
        progress.progress((i+1)/len(prices))
    ranking=pd.DataFrame(rows).sort_values('score',ascending=False,na_position='last')
    st.session_state['hybrid_ranking']=ranking
if 'hybrid_ranking' in st.session_state:
    ranking=st.session_state['hybrid_ranking']
    st.dataframe(ranking.rename(columns={'ticker':'Símbolo','score':'Score /100','coverage':'Cobertura %'}),hide_index=True,use_container_width=True)
    st.download_button('Descargar ranking CSV',ranking.to_csv(index=False).encode('utf-8'),file_name='ranking_actual_v06.csv')
    allocations,cash=propose_allocation(ranking.to_dict('records'),capital,positions,max_weight,cash_floor,minimum_score,minimum_coverage)
    st.subheader('Propuesta de asignación · simulación sin órdenes')
    if allocations: st.dataframe(pd.DataFrame(allocations),hide_index=True,use_container_width=True)
    else: st.info('Ningún instrumento supera los umbrales; el modelo propone mantener efectivo.')
    st.metric('Efectivo simulado no asignado',f'US${cash:,.2f}')
    st.caption('Es una propuesta calculada al consultar, no una cartera ejecutada ni persistente. Sin historial de órdenes, sin conexión a broker y sin rentabilidad real.')

st.subheader('Posicionamiento institucional / Smart Money')
st.info('Aún sin índice automático: se requieren posiciones 13F fechadas, identificadores de emisor, ajustes por splits y fecha efectiva de publicación. No asignamos puntuaciones inventadas.')
st.caption('Los 13F reflejan posiciones declaradas con retraso y cobertura incompleta; no constituyen señales Buy/Sell. Un índice real necesita historial punto-en-tiempo para evitar sesgo retrospectivo.')
st.subheader('Estado')
st.write('🟢 Backtest comparativo de 12 meses · 🟢 Ranking híbrido actual · 🟡 Smart Money sin datos 13F verificados · 🔴 Trading autónomo y broker desactivados')
st.caption('No publiques claves ni información de broker en GitHub.')
