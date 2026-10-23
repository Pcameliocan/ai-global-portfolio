# AI Global Portfolio Manager — v0.3

Streamlit prototype for quantitative screening and hypothetical allocation of a USD 5,000 global portfolio.

## Deploy

Replace the three files in the root of your GitHub repository (`app.py`, `requirements.txt`, `README.md`). Streamlit Community Cloud should redeploy on commit. Entry point: `app.py`.

## Limitations

- Historical third-party data can be stale or unavailable; no guarantee of real-time quotes.
- Momentum/volatility scoring is deterministic, not an AI investment adviser.
- Hypothetical allocations only. No live orders, brokerage connection, persistent state, or verified backtest.
- Never commit secrets or API keys. Do not use this dashboard for live trading.
