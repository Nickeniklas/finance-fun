# CLAUDE.md

Guidance for Claude Code working in this repo. Read `docs/PLAN.md`,
`docs/DATA_MODULE.md`, and `docs/PROMPT_LIBRARY.md` for full detail — this file is the
quick operating brief.

## What we're building
A public (no-login) finance site: compare stocks, finance news, favorite tickers with
a price line chart, and a curated copy-only prompt library. See `docs/PLAN.md`.

## Stack (decided — do not re-litigate without being asked)
- Frontend: **vanilla HTML/CSS/JS** (no framework — owner does not write React)
- Charts: **TradingView Lightweight Charts** (plain JS; drawing only, no fetching)
- Backend: **Python + FastAPI**
- Hosting: **Railway**
- Data: **Finnhub free tier** (60 calls/min) via the `finnhub-python` client
- Favorites: **browser localStorage** (no accounts, no DB in v1)
- Prompt library: **static JSON** in repo, read-only
- LLM: **none in v1** (v2 = user's own API key, browser-side only)

## Hard rules
- **Only the data module talks to Finnhub.** Everything else goes through it.
- **Cache every Finnhub call** with the TTL from `docs/DATA_MODULE.md`. We live on a
  60/min free tier — caching is not optional.
- **Reshape Finnhub responses** into the clean output shapes in `docs/DATA_MODULE.md`.
  The frontend must never see Finnhub's raw/terse fields.
- **Charts show completed daily closes (through yesterday).** Live price goes in the
  watchlist display, not the chart.
- **Prompt library is standalone** — it must not depend on the data layer in v1.
- **No accounts, no database, no server-side LLM calls in v1.**
- Keep v1 from blocking any v2 item (own-key prompt running, FMP fundamentals,
  real accounts). Don't paint us into a corner.

## Current state (update this as steps complete)

- [x] Step 1 — FastAPI skeleton (`main.py`, `Procfile`, `requirements.txt`), `/health`
      endpoint live, `FINNHUB_API_KEY` read from env but not used yet.
- [ ] Step 2 — Data module + `/quote/{symbol}` (next)
- [ ] Step 3 — Remaining endpoints: candles, fundamentals, news
- [ ] Step 4 — Frontend shell, watchlist (localStorage), one chart
- [ ] Step 5 — Compare view, news view
- [ ] Step 6 — Prompt library (static JSON + copy UI)

## Build order (suggested)
1. ~~FastAPI skeleton deployable to Railway (one live endpoint).~~ **Done.**
2. Data module + `/quote/{symbol}` end to end, with cache.
3. Remaining endpoints: candles, fundamentals (`company_basic_financials`), news.
4. Frontend shell + watchlist (localStorage) + one chart.
5. Compare view, news view.
6. Prompt library (static JSON + copy UI).

## Gotchas
- Candle `from`/`to` are UNIX timestamps; client returns parallel arrays (`c`, `t`) —
  zip into `{ time, value }` for TradingView.
- `company_news` takes a date range; pass ~last 7 days, not a huge window.
- In-process dict cache is fine for v1 (vanishes on restart). Redis only if we ever
  run multiple instances.
- Secrets: the Finnhub API key is an env var on Railway. Never commit it.
