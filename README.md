# AI Global Portfolio Manager v0.7

Aplicación educativa de análisis y simulación. No envía órdenes a brokers ni mantiene una cartera real.

## Instalación
Subir al directorio raíz del repositorio **todos** los archivos `.py` y `requirements.txt`. Streamlit ejecuta `app.py`.

## Cambios
- Universo ampliado a tecnología, salud, finanzas, energía, industria y consumo.
- Separación entre score y cobertura/confianza; cobertura mínima obligatoria para proponer compras.
- Límites por instrumento, sector simplificado y mínimo de efectivo.
- Smart Money opcional a partir de CSV aportado por el usuario, con columnas `ticker,manager,report_date,filing_date,shares,previous_shares`. No se consultan automáticamente reportes SEC ni se validan splits. Cambios en tenencias declaradas NO son órdenes ni señales de compra en tiempo real.
- Panel temporal para exportar diagnóstico ZIP (ranking, asignación, curvas, métricas, rebalanceos y calidad de precios). Ejecutar ranking y backtest antes de exportar.

## Limitaciones
Backtesting de 12 meses sigue usando **proxies basados en precios**, no el score híbrido actual ni posiciones 13F actuales. La simulación no incluye spreads, impuestos ni impacto de mercado. Universo fijo: sesgo de supervivencia. El ranking puede usar datos de proveedor con retrasos o errores. No hay ejecución ni persistencia en la nube.


## Versión 0.8
- Universo configurado vs. instrumentos con datos: tabla de auditoría y CSV. Los motivos de exclusión siguen agrupados.
- Límite por temática correlacionada (clasificación manual conservadora) además de límite sectorial.
- Banda opcional de sustitución por score para posiciones **simuladas**; no modifica el backtest histórico.
- Comparador ilustrativo SPY 80% + efectivo 20% vs SPY 100% y momentum; no incluye rendimiento del efectivo.
- Consenso: se informa cantidad de analistas y fecha en consulta individual, cuando proveedor los suministra. No se confunde Strong Buy con unanimidad.
- Diagnóstico incluye auditoría del universo y benchmark mixto, cuando se ejecutan las funciones. Identificador de versión corregido.
- 13F: CSV manual sin validación automática SEC. No se conecta a brokers ni ejecuta operaciones.

**Instalación:** subir todos los archivos de este ZIP a la raíz del repositorio. Ejecutar comparación y ranking antes de exportar diagnóstico.
