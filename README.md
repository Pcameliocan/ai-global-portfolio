# AI Global Portfolio Manager v0.4

Demo educativa con datos históricos de Yahoo Finance, ranking y backtesting exploratorio mensual. **No es trading autónomo** ni opera dinero real.

## Despliegue

Subir `app.py`, `backtest.py`, `requirements.txt` y `README.md` a la raíz del repositorio GitHub existente, sustituyendo los archivos anteriores. En Streamlit Community Cloud conservar `app.py` como archivo principal. El backtest se inicia desde el botón de la aplicación.

## Límites

El backtest usa un universo elegido hoy (sesgo de supervivencia/selección), precios ajustados, una intersección de días comunes y costos simplificados. La referencia SPY es solo una comparación; los retornos no predicen resultados futuros. No hay base de datos persistente, programador cloud, broker ni modelo LLM. No guardar credenciales en GitHub.
