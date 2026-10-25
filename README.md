# AI Global Portfolio Manager v0.9 — autonomous PAPER ONLY

La versión 0.9 mantiene la interfaz de la v0.8 (ranking híbrido, comparador de 12 meses, diagnóstico) y añade un motor diario independiente con registro persistente en Supabase. **No conecta brokers ni cursa órdenes reales.**

## Arquitectura

GitHub Actions (`.github/workflows/paper_daily.yml`) → `daily_worker.py` → `hybrid.py` + `risk_v08.py` → `paper_engine.py` → Supabase PostgreSQL (RPC transaccional) → panel Streamlit (`app.py`, lectura).

- Ejecuta a las **23:30 UTC, lunes a viernes** (después del cierre regular de EE. UU.); los festivos quedan sin operación. GitHub Actions puede retrasar u omitir ejecuciones programadas. No es un sistema de trading en tiempo real.
- El primer día **solo genera una señal**; la señal se llena en la siguiente fecha bursátil observada usando su **cierre ajustado**, como aproximación retrospectiva. Este precio no es una cotización ejecutable ni un precio real de broker. No hay anticipación de datos para la señal.
- Guarda `paper_state` (efectivo, fracciones de acciones, señal pendiente), `paper_runs` (equity, efectivo, benchmark SPY, ranking y explicación) y `paper_trades` (compras/ventas simuladas y comisión).
- Evita ejecutar dos veces la misma fecha bursátil y utiliza una función SQL transaccional con bloqueo y control de versión. Si falla un precio de una posición o hay una señal inválida, **no registra cambios**.
- Mantiene efectivo mínimo 20%, máximo 20% por acción, 30% sector, 30% temática y máximo seis posiciones; costos simulados 0,10% por transacción, mínimo US$25 por orden. Las etiquetas sectoriales/temáticas son aproximadas y no descomponen ETF.
- **No hay datos institucionales 13F automáticos** en el worker: sin 13F validado, el factor no se puntúa. Los fundamentales y recomendaciones de Yahoo Finance son snapshots actuales, no históricos punto-en-tiempo.

## Configuración inicial (desde iPhone o computador)

1. Crea un proyecto gratuito en [Supabase](https://supabase.com/) y abre **SQL Editor**. Pega y ejecuta **todo** el archivo `schema.sql` una sola vez. Se crea un portafolio inicial con US$5.000 en efectivo. No ejecutes de nuevo una versión distinta de `schema.sql` sin respaldar tus datos.
2. En Supabase → **Project Settings / API**, copia **Project URL** y la **service_role key** (o Secret API key equivalente que pueda escribir por PostgREST). **No compartas la clave ni la subas a GitHub.**
3. Sube los archivos del ZIP a la **raíz del repositorio** GitHub, y el archivo de workflow en la ruta exacta `.github/workflows/paper_daily.yml`. La interfaz web de GitHub en móvil puede requerir *Add file → Upload files* o crear carpetas desde el editor.
4. En GitHub → repositorio → **Settings → Secrets and variables → Actions → New repository secret**, crea `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY`.
5. En Streamlit Community Cloud → **Manage app → Settings → Secrets**, añade (sin comillas especiales):
   ```toml
   SUPABASE_URL = "https://TU-PROYECTO.supabase.co"
   SUPABASE_SERVICE_ROLE_KEY = "TU-CLAVE-SECRETA"
   ```
   La clave se usa únicamente en el servidor Streamlit; **no la muestres en pantalla, logs o exportaciones**. Si el dashboard es público, el contenido simulado que muestre puede ser visible públicamente; restringe acceso antes de cargar información sensible.
6. En GitHub → **Actions → Daily paper portfolio → Run workflow**, ejecuta manualmente una vez. El primer día crea una **señal pendiente**, no compra. En el siguiente día bursátil, ejecutará las compras simuladas al cierre observado.
7. Abre Streamlit y busca **Agente autónomo · paper trading diario**. El registro se leerá desde Supabase y persistirá entre reinicios de la app.

## Validación

Ejecuta `python -m unittest discover -p 'tests_paper.py' -v` para pruebas locales sin acceso a red. Se verifican ejecución diferida, comisión, efectivo mínimo, rechazo de objetivos inválidos y datos faltantes.

## Limitaciones importantes

- Yahoo Finance no ofrece garantías de disponibilidad, precios o integridad. El motor usa cierres ajustados (incluyen ajustes por dividendos/splits) y **no** modela el flujo real de dividendos ni eventos corporativos de manera completa. La rentabilidad es orientativa.
- La lógica de asignación es heurística y el backtest previo no ha demostrado superar SPY. No se deben interpretar señales como asesoramiento de inversión.
- GitHub Actions es un programador de tareas **best-effort**, no infraestructura 24/7. Si una ejecución falla, revisa logs y vuelve a lanzarla. La idempotencia impide duplicar el mismo día.
- El portafolio inicia al crear el esquema. **No reinicies manualmente la tabla** si ya existen operaciones.
- El panel v0.8 manual y el agente persistente son secciones distintas. El ranking manual no modifica la base de datos ni ejecuta órdenes.
- Las tablas tienen RLS activado y no conceden lectura a `anon`. La clave `service_role` es altamente privilegiada: mantenla exclusivamente en secretos de servidores.

## Archivos principales

- `app.py`: Streamlit con panel de historial persistente de solo lectura.
- `daily_worker.py`: evaluación diaria.
- `paper_engine.py`: ejecución simulada diferida, costos y restricciones.
- `supabase_store.py`: cliente HTTP y RPC.
- `schema.sql`: esquema y operación atómica.
- `portfolio_config.py`: universo y sectores compartidos.
- `.github/workflows/paper_daily.yml`: programación y ejecución manual.
- `tests_paper.py`: pruebas sin conexión.
