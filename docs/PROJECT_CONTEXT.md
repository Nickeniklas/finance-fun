# Project Context

Quick-reference facts for a fresh chat that hasn't read the full plan.

---

## What this is

A public (no-login) finance site: compare stocks, finance news, favorite tickers with
a price chart, and a curated copy-only prompt library. See `PLAN.md` for full detail.

## Hosting

**Render free tier.** Railway has no real free tier (trial credit only, ~$5/mo after).
Render's ~1-min cold start on idle is an accepted tradeoff for a low-traffic hobby site.

## Data providers (two — not one)

| Data type | Provider | Why |
|---|---|---|
| Quote, news, fundamentals, profile | **Finnhub** (free tier, 60 calls/min) | Primary provider |
| Daily candle history | **yfinance** | Deliberate exception — see below |

**Candles use yfinance by design.** Finnhub moved `stock/candle` off the free tier;
it returns 403 for US equities. This is permanent. Alpha Vantage free (25 req/day) is
unusable for a public site. yfinance fills the gap for candles only. The data module
boundary is preserved — nothing outside `data.py` touches either provider. If yfinance
breaks, the chart endpoint returns an empty series rather than crashing.

## Build status

- [x] Step 1 — FastAPI skeleton, `/health`, Render deploy pipeline
- [x] Step 2 — Data module: `get_quote`, cache, `/quote/{symbol}`
- [x] Step 3 — Remaining endpoints: candles, fundamentals, profile, news
- [x] Step 4 — Frontend shell (`static/`): watchlist (localStorage), live prices, 90-day chart
- [ ] Step 5 — Compare view, news view
- [ ] Step 6 — Prompt library (static JSON + copy UI)

## Hard constraints (do not re-litigate without asking)

- Vanilla HTML/CSS/JS frontend — owner does not write React
- No accounts, no database, no server-side LLM calls in v1
- All provider calls go through `data.py` — frontend never calls Finnhub or yfinance
- Cache every external call (TTLs in `DATA_MODULE.md`)
- Finnhub API key lives only in Render's environment variables — never in code
