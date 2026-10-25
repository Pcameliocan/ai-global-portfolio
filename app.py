import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import io
import json
import zipfile
from datetime import datetime, timezone
from portfolio_engine import MODELS, simulate_models, metrics, signals
from hybrid import calculate_score, propose_allocation
from smart_money import score_13f
from risk_v08 import allocate_with_theme, confidence, benchmark_cash_curve, THEMES

st.set_page_config(page_title='AI Global Portfolio v0.9',page_icon='🌍',layout='wide')
st.title('🌍 AI Global Portfolio Manager')
st.caption('v0.9 · Comparador 12 meses + ranking híbrido actual · SOLO SIMULACIÓN, SIN BROKER')
st.warning('Los modelos históricos son aproximaciones cuantitativas, NO réplicas de AQR, Dimensional o BlackRock. Sin recomendaciones personalizadas ni operaciones reales.')
from portfolio_config import UNIVERSE, SECTORS

# Los ETF sectoriales cuentan como exposición propia; no se descompone su composición.

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
    sector_cap=st.slider('Máximo por sector / exposición %',15,60,30,5)/100
    theme_cap=st.slider('Máximo por temática correlacionada %',15,60,30,5)/100
    replacement_margin=st.slider('Diferencia mínima de score para sustituir una posición (puntos)',0,20,7,1)
    st.caption('El backtest evalúa los últimos 12 meses. Descarga datos anteriores solo para construir indicadores.')
if st.button('Actualizar precios'):
    load_prices.clear()
with st.spinner('Descargando historial de precios...'):
    prices,missing=load_prices()
if missing: st.info('Sin historial suficiente: '+', '.join(missing))
st.caption(f'Universo configurado: {len(UNIVERSE)} | Con historial suficiente: {len(prices)} | Excluidos: {len(missing)}')
with st.expander('Auditoría del universo y exclusiones'):
    audit_rows=[{'Símbolo':t,'Mercado':label,'Estado':'Elegible por historial' if t in prices else 'Excluido: historial insuficiente o descarga fallida','Observaciones':len(prices[t]) if t in prices else None} for t,label in UNIVERSE.items()]
    st.dataframe(pd.DataFrame(audit_rows),hide_index=True,use_container_width=True)
    st.session_state['diag_universe']=pd.DataFrame(audit_rows)
    st.caption('Los motivos se agrupan en esta versión; el proveedor no distingue siempre falta de historial de errores de red.')
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
        st.session_state['diag_curve']=curve.copy()
        st.session_state['diag_trades']=trades.copy()
        st.line_chart(curve)
        if 'SPY' in curve.columns:
            mix=benchmark_cash_curve(curve['SPY'],capital,cash_weight=.20)
            comparison=pd.DataFrame({'SPY 80% + efectivo 20%':mix,'SPY 100%':curve['SPY'],'Momentum actual':curve['Momentum actual']})
            st.session_state['diag_benchmark_mix']=comparison.copy()
            st.caption('Comparación adicional hipotética: SPY 80% + efectivo 20%, sin intereses sobre efectivo ni costos. No es una estrategia optimizada.')
            st.line_chart(comparison)
        stats=pd.DataFrame([{'Modelo':k,**metrics(curve[k],capital)} for k in curve.columns])
        st.session_state['diag_stats']=stats.copy()
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
            st.caption(f"Clasificación agregada del proveedor; analistas reportados: {d.get('Analistas') or 'sin dato'}; consulta UTC: {d.get('Fecha consulta (UTC)','sin fecha')}. Un 100 no significa unanimidad.")
        else: st.info('No hay recomendación convertible a puntuación.')
    else: st.info('Proveedor sin datos fundamentales para este instrumento.')

st.subheader('Smart Money · declaraciones 13F verificables')
st.caption('Carga opcional de CSV con ticker, manager, report_date, filing_date, shares, previous_shares. Solo declaraciones ya publicadas, fechadas y verificadas por el usuario. No es un indicador de compras en tiempo real.')
file_13f=st.file_uploader('CSV institucional (opcional)',type=['csv'],key='institutional_upload')
inst_scores={}
if file_13f is not None:
    try:
        data_13f=pd.read_csv(file_13f)
        scored_13f=score_13f(data_13f)
        st.session_state['diag_institutional']=scored_13f
        st.dataframe(scored_13f,hide_index=True,use_container_width=True)
        inst_scores=dict(zip(scored_13f['ticker'],scored_13f['Institucionales']))
        st.info('Los datos del CSV son aportados por el usuario; no se han contrastado automáticamente con SEC EDGAR. Verifica las fuentes antes de confiar en el indicador.')
    except Exception as exc:
        st.error(f'CSV institucional no válido: {exc}')

st.subheader('Ranking híbrido actual · v0.8')
st.caption('Puntuaciones actuales, NO backtest. Pesos: momentum 35%, calidad 25%, valoración 15%, analistas 15%, institucionales 10%. Sin fuente 13F validada, el componente institucional queda sin puntuación. El score se normaliza por factores disponibles y se informa su cobertura.')
with st.expander('Reglas de selección simulada',expanded=False):
    minimum_score=st.slider('Score mínimo',50,95,65,5)
    minimum_coverage=st.slider('Cobertura mínima de datos %',35,100,65,5)
    held_tickers=st.text_input('Posiciones simuladas actuales, separadas por coma (opcional)',value='',help='Solo para evitar reemplazos por diferencias pequeñas de puntuación; no se conecta a un broker.')
if st.button('Calcular ranking híbrido actual',type='primary'):
    rows=[]
    progress=st.progress(0)
    for i,(ticker,series) in enumerate(prices.items()):
        try:
            info=yf.Ticker(ticker).info or {}
            result=calculate_score(series,info,institutional=inst_scores.get(ticker))
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
    ranking=ranking.copy()
    ranking['Confianza']=ranking['coverage'].apply(confidence)
    ranking['Tema de riesgo']=ranking['ticker'].map(THEMES).fillna('Sin clasificar')
    st.dataframe(ranking.rename(columns={'ticker':'Símbolo','score':'Score /100','coverage':'Cobertura %'}),hide_index=True,use_container_width=True)
    st.download_button('Descargar ranking CSV',ranking.to_csv(index=False).encode('utf-8'),file_name='ranking_actual_v06.csv')
    sector_map={t:SECTORS.get(t,'Sin clasificar') for t in prices}
    allocations,cash=allocate_with_theme(ranking.to_dict('records'),capital,positions,max_weight,cash_floor,minimum_score,minimum_coverage,sector_cap,sector_map,theme_cap=theme_cap,current_positions=[x.strip().upper() for x in held_tickers.split(',') if x.strip()],replacement_margin=replacement_margin)
    st.subheader('Propuesta de asignación · simulación sin órdenes')
    if allocations: st.dataframe(pd.DataFrame(allocations),hide_index=True,use_container_width=True)
    else: st.info('Ningún instrumento supera los umbrales; el modelo propone mantener efectivo.')
    st.session_state['diag_allocations']=pd.DataFrame(allocations)
    st.session_state['diag_cash']=float(cash)
    st.metric('Efectivo simulado no asignado',f'US${cash:,.2f}')
    st.caption('Los límites sectoriales y temáticos usan clasificaciones manuales aproximadas: no capturan todas las correlaciones ni exposiciones indirectas de ETF. Es una propuesta calculada al consultar, no una cartera ejecutada ni persistente. Sin historial de órdenes, sin conexión a broker y sin rentabilidad real.')

st.subheader('Alcance del Smart Money')
st.info('Solo se puntúan declaraciones 13F aportadas mediante CSV y fechadas. No hay integración automática con SEC ni comprobación de splits o identificadores; sin CSV el factor queda sin puntuar.')
st.caption('Los 13F reflejan posiciones declaradas con retraso y cobertura incompleta; no constituyen señales Buy/Sell. Un índice real necesita historial punto-en-tiempo para evitar sesgo retrospectivo.')

st.subheader('Exportación temporal para diagnóstico')
with st.expander('📦 Exportar datos para mejorar el modelo', expanded=False):
    st.caption('Descarga un ZIP con los resultados disponibles en esta sesión. Puedes adjuntarlo aquí para revisar puntuaciones, diversificación, backtesting y errores de cobertura. No incluye contraseñas, tokens ni credenciales.')
    st.caption('Primero ejecuta el ranking y la comparación histórica para incluir ambos resultados.')
    diag_files = {}
    manifest = {
        'app_version': '0.9',
        'export_utc': datetime.now(timezone.utc).isoformat(),
        'capital_simulado_usd': float(capital),
        'max_posiciones': int(positions),
        'max_sector': float(sector_cap),
        'max_tematica': float(theme_cap),
        'margen_reemplazo_score': int(replacement_margin),
        'max_peso_por_instrumento': float(max_weight),
        'efectivo_minimo': float(cash_floor),
        'score_minimo': int(minimum_score),
        'cobertura_minima': int(minimum_coverage),
        'universo': list(UNIVERSE.keys()),
        'instrumentos_con_historial': list(prices.keys()),
        'instrumentos_sin_historial': list(missing),
        'fuente_precios': 'Yahoo Finance mediante yfinance',
        'notas': 'Solo simulacion. No contiene operaciones reales ni historial 13F.',
    }
    if 'diag_cash' in st.session_state:
        manifest['efectivo_propuesto_usd'] = st.session_state['diag_cash']
    diag_files['resumen.json'] = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    price_rows = []
    for symbol, series in prices.items():
        valid = series.dropna()
        price_rows.append({
            'ticker': symbol, 'observaciones': int(len(valid)),
            'primera_fecha': str(valid.index.min().date()) if len(valid) else '',
            'ultima_fecha': str(valid.index.max().date()) if len(valid) else '',
            'ultimo_cierre_ajustado': float(valid.iloc[-1]) if len(valid) else None,
            'faltantes': int(series.isna().sum()),
        })
    diag_files['calidad_precios.csv'] = pd.DataFrame(price_rows).to_csv(index=False).encode('utf-8-sig')
    for key, filename in [
        ('hybrid_ranking', 'ranking_completo.csv'),
        ('diag_allocations', 'cartera_propuesta.csv'),
        ('diag_stats', 'metricas_backtest.csv'),
        ('diag_curve', 'curvas_backtest.csv'),
        ('diag_trades', 'rebalanceos_backtest.csv'),
        ('diag_benchmark_mix', 'benchmark_spy_efectivo.csv'),
        ('diag_universe', 'auditoria_universo.csv'),
        ('diag_institutional','institucional_aportado.csv'),
    ]:
        value = st.session_state.get(key)
        if isinstance(value, pd.DataFrame):
            diag_files[filename] = value.to_csv(index=(key == 'diag_curve')).encode('utf-8-sig')
    diag_files['LEEME.txt'] = (
        'Diagnostico AI Global Portfolio v0.9\\n'
        'Archivos presentes dependen de los calculos ejecutados en esta sesion.\\n'
        'No incluye claves, credenciales, cartera real ni datos institucionales historicos.\\n'
        'El ranking es actual; el backtest usa aproximaciones historicas de precios.\\n'
    ).encode('utf-8')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename, data in diag_files.items():
            zf.writestr(filename, data)
    st.write('Archivos incluidos:', ', '.join(diag_files.keys()))
    st.download_button(
        'Descargar diagnóstico ZIP',
        data=archive.getvalue(),
        file_name='diagnostico_ai_global_portfolio.zip',
        mime='application/zip',
        key='download_diagnostic_zip',
    )

st.subheader('Agente autónomo · paper trading diario')
st.caption('Lectura del registro persistente en Supabase. Las decisiones se calculan en GitHub Actions, no desde el navegador. No existen órdenes reales.')
try:
    from supabase_store import Store
    if 'SUPABASE_URL' in st.secrets and 'SUPABASE_SERVICE_ROLE_KEY' in st.secrets:
        paper_store=Store(st.secrets['SUPABASE_URL'],st.secrets['SUPABASE_SERVICE_ROLE_KEY'])
        paper_state=paper_store.state()
        paper_runs=pd.DataFrame(paper_store.runs(180))
        paper_trades=pd.DataFrame(paper_store.trades(300))
        st.metric('Efectivo persistente USD',f"${float(paper_state['cash']):,.2f}")
        st.write('Posiciones simuladas:',paper_state.get('holdings',{}))
        st.write('Próxima asignación pendiente:',paper_state.get('pending') or 'Sin señales aún')
        if not paper_runs.empty:
            paper_runs=paper_runs.sort_values('market_date')
            st.line_chart(paper_runs.set_index('market_date')[['equity']])
            st.dataframe(paper_runs[['market_date','equity','cash','rationale']].tail(20),hide_index=True,use_container_width=True)
            st.download_button('Exportar registro diario CSV',paper_runs.to_csv(index=False).encode('utf-8-sig'),file_name='paper_runs.csv')
        if not paper_trades.empty:
            st.dataframe(paper_trades.head(40),hide_index=True,use_container_width=True)
            st.download_button('Exportar operaciones simuladas CSV',paper_trades.to_csv(index=False).encode('utf-8-sig'),file_name='paper_trades.csv')
    else:
        st.info('El historial persistente aparecerá cuando configures Supabase en los Secrets de Streamlit.')
except Exception as exc:
    st.warning('No fue posible leer el historial persistente. Revisa configuración o conectividad de Supabase.')

st.subheader('Estado')
st.write('🟢 Backtest 12 meses · 🟢 Límites sectoriales y temáticos · 🟢 Exportación diagnóstico · 🟡 Smart Money CSV manual · 🔴 Trading y broker desactivados')
st.caption('No publiques claves ni información de broker en GitHub.')
