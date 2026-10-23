# AI Global Portfolio Manager v0.5

Dashboard educativo de Streamlit para comparar **cuatro estrategias proxy** durante los **últimos 12 meses**, con historial anterior usado solo para calcular señales. Ninguna operación real ni integración de broker.

## Instalación

Sube `app.py`, `backtest.py`, `requirements.txt` y `README.md` a la raíz del repositorio GitHub existente. Streamlit Community Cloud ejecuta `app.py`. Si no se actualiza, usa Reboot app.

## Alcance

- Cuatro estrategias **proxy basadas solo en precios** (NO reproducciones fieles de AQR o Dimensional ni un modelo fundamental histórico).
- Ventana de evaluación de 12 meses, datos de 3 años para indicadores de hasta 12 meses.
- Señales calculadas con precios del cierre previo; rebalanceo aproximado en el cierre siguiente. Sin ejecución intradía.
- Costo estimado de 10 bps por rotación; no incluye spread, impuestos ni impacto de mercado.
- Comparación con SPY, Sharpe sin tasa libre de riesgo, drawdown, volatilidad y registro de rebalanceos.
- Consulta **actual** de recomendación agregada, número de analistas, precio objetivo, P/E forward, ROE, crecimiento de ingresos y deuda/patrimonio desde Yahoo Finance. Datos opcionales y no garantizados.
- **Smart Money no implementado** hasta contar con fuente 13F histórica y fechas de publicación. Nunca se rellenan puntuaciones ficticias.

## Limitaciones importantes

Universo fijo actual y solo 12 meses de evaluación: sesgo de selección/supervivencia y evidencia estadística limitada. Los indicadores proxy de valoración (reversión de precios) **no miden múltiplos de valoración**. Datos actuales de analistas y balances no se inyectan al pasado. ETFs y acciones mezclados: sus métricas fundamentales no son comparables. El precio puede estar retrasado o faltar. Simulación sin persistencia, sin automatización diaria, sin órdenes reales. No subir secretos a GitHub.


## Reparación de importación
Esta distribución usa `portfolio_engine.py` como módulo de cálculo para evitar
conflictos con versiones anteriores de `backtest.py`. Subir **juntos**
`app.py` y `portfolio_engine.py` al directorio raíz de GitHub.
`backtest.py` se conserva por compatibilidad y no es utilizado por `app.py`.
