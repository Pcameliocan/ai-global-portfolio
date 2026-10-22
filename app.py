import streamlit as st
import pandas as pd

st.set_page_config(page_title='AI Global Portfolio Manager', page_icon='🌍', layout='wide')
st.title('🌍 AI Global Portfolio Manager')
st.caption('Versión 0.2 · DEMOSTRACIÓN · Sin datos de mercado en vivo ni operaciones reales')
st.warning('SIMULACIÓN: los instrumentos y montos son ilustrativos. No son recomendaciones ni órdenes de compra.')

INITIAL = 5000.0
assets = pd.DataFrame([
    {'Símbolo':'SPY','Tipo':'ETF EE. UU.','Monto USD':1000.0},
    {'Símbolo':'VXUS','Tipo':'ETF internacional','Monto USD':750.0},
    {'Símbolo':'BABA','Tipo':'Acción China (ADR)','Monto USD':500.0},
    {'Símbolo':'ASML','Tipo':'Acción Europa (ADR)','Monto USD':500.0},
    {'Símbolo':'MSFT','Tipo':'Acción EE. UU.','Monto USD':500.0},
    {'Símbolo':'Efectivo','Tipo':'Reserva','Monto USD':1750.0},
])
assets['Peso %'] = (assets['Monto USD'] / INITIAL * 100).round(1)

with st.sidebar:
    st.header('Configuración de prueba')
    max_weight = st.slider('Exposición máxima por instrumento (%)', 5, 40, 20, 5)
    min_cash = st.slider('Efectivo mínimo (%)', 0, 50, 10, 5)
    st.info('Los controles solo verifican la cartera ilustrativa. No envían órdenes.')

c1, c2, c3 = st.columns(3)
c1.metric('Capital de referencia', 'US$5.000')
c2.metric('Exposición ilustrativa', f"{100-assets.loc[assets['Símbolo']=='Efectivo','Peso %'].iloc[0]:.1f}%")
c3.metric('Rentabilidad', 'No disponible', help='Aún no existe un historial de operaciones o cotizaciones.')

st.subheader('Cartera de demostración')
st.dataframe(assets, hide_index=True, use_container_width=True)
st.bar_chart(assets.set_index('Símbolo')['Monto USD'])

holdings = assets[assets['Símbolo'] != 'Efectivo']
cash_pct = float(assets.loc[assets['Símbolo']=='Efectivo','Peso %'].iloc[0])
violations = holdings[holdings['Peso %'] > max_weight]
st.subheader('Comprobación de límites')
if not violations.empty:
    st.error('Hay instrumentos que superan el límite seleccionado: ' + ', '.join(violations['Símbolo']))
else:
    st.success('Ningún instrumento supera el límite individual seleccionado.')
if cash_pct < min_cash:
    st.error(f'Efectivo ilustrativo ({cash_pct:.1f}%) por debajo del mínimo ({min_cash}%).')
else:
    st.success(f'Efectivo ilustrativo ({cash_pct:.1f}%) cumple el mínimo ({min_cash}%).')

st.subheader('Estado de módulos')
st.write('🟢 Dashboard ilustrativo · 🟡 Datos en vivo pendientes · 🟡 Backtesting pendiente · 🔴 Broker desconectado · 🔴 Trading real desactivado')
st.caption('Proyecto educativo y de desarrollo. No garantiza rentabilidad ni representa asesoría financiera personalizada.')
