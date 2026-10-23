# AI Global Portfolio Manager v0.6

Actualiza el repositorio Streamlit con **todos los archivos de este ZIP** en la raíz del proyecto. `app.py` importa `portfolio_engine.py` y `hybrid.py`. No elimines esos módulos.

## Funcionalidad

- Conserva el backtesting exploratorio de 12 meses de cuatro modelos y SPY de v0.5.
- Nuevo ranking híbrido **actual** con momentum, calidad, valoración y recomendación agregada de analistas, consultados con yfinance/Yahoo Finance. El quinto factor, Smart Money, se mantiene sin dato hasta contar con posiciones 13F verificadas y fechadas.
- Informa **cobertura** para que no se confunda un score basado en pocos factores con una evaluación completa.
- Propone una asignación simulada de US$5.000 con topes por posición, efectivo mínimo y umbrales de score/cobertura. No genera órdenes ni conserva un libro de transacciones.
- Datos actuales **nunca** se aplican a fechas históricas del backtest. Los modelos históricos siguen siendo proxies basados en precios y no replican estrategias propietarias.

## Instalación desde GitHub

Subir juntos `app.py`, `hybrid.py`, `portfolio_engine.py`, `backtest.py`, `requirements.txt`, `README.md`; confirmar en la rama main. Streamlit se actualiza con el commit. Abrir el dashboard y pulsar **Calcular ranking híbrido actual**. Los datos de Yahoo pueden faltar o fallar por límites del proveedor.

## Limitaciones

Los datos fundamentales y ratings pueden estar desactualizados, incompletos o ser inapropiados para ETFs. Las puntuaciones son heurísticas de investigación, no una estimación estadística de retornos. No existe backtest punto-en-tiempo para el nuevo score. No usar para operar dinero real.
