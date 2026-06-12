# CLAUDE.md

Guidance for Claude Code working in this repo. Read `docs/PROJECT_CONTEXT.md` first for
a fast orient, then `docs/PLAN.md`, `docs/DATA_MODULE.md`, and `docs/PROMPT_LIBRARY.md`
for full detail — this file is the quick operating brief.

## What we're building
A public (no-login) finance site: compare stocks, finance news, favorite tickers with
a price line chart, and a curated copy-only prompt library. See `docs/PLAN.md`.

## Stack (decided — do not re-litigate without being asked)
- Frontend: **vanilla HTML/CSS/JS** (no framework — owner does not write React)
- Charts: **TradingView Lightweight Charts** (plain JS; drawing only, no fetching)
- Backend: **Python + FastAPI**
- Hosting: **Render** (free tier)
- Data: **Finnhub free tier** (60 calls/min) via `finnhub-python` · **yfinance** for candles (deliberate exception — see Gotchas)
- Favorites: **browser localStorage** (no accounts, no DB in v1)
- Prompt library: **static JSON** in repo, read-only
- LLM: **none in v1** (v2 = user's own API key, browser-side only)

## Hard rules
- **Only the data module talks to external data providers.** Everything else goes
  through it. Providers: Finnhub (quote, news, fundamentals, profile) + yfinance
  (candles only — deliberate exception, see below).
- **Cache every provider call** with the TTL from `docs/DATA_MODULE.md`. Finnhub is
  60/min free tier — caching is not optional. Same discipline applies to yfinance.
  All data endpoints are also rate-limited via **slowapi** (candles: 20/min;
  quote/fundamentals/profile/news: 60/min) to protect the unofficial yfinance
  scraping from symbol-enumeration abuse that per-symbol caching cannot block.
- **Reshape all provider responses** into the clean output shapes in `docs/DATA_MODULE.md`.
  The frontend must never see Finnhub's raw/terse fields or yfinance DataFrames.
- **Charts show completed daily closes (through yesterday).** Live price goes in the
  watchlist display, not the chart.
- **Prompt library is standalone** — it must not depend on the data layer in v1.
- **No accounts, no database, no server-side LLM calls in v1.**
- Keep v1 from blocking any v2 item (own-key prompt running, FMP fundamentals,
  real accounts). Don't paint us into a corner.

## Current state (update this as steps complete)

- [x] Step 1 — FastAPI skeleton (`main.py`, `Procfile`, `requirements.txt`), `/health`
      endpoint live, `FINNHUB_API_KEY` read from env but not used yet.
- [x] Step 2 — Data module (`data.py`) + `/quote/{symbol}`, in-process cache, Finnhub
      reshaping. `python-dotenv` wired for local `.env`.
- [x] Step 3 — Remaining endpoints: `/candles/{symbol}` (yfinance), `/fundamentals/{symbol}`,
      `/profile/{symbol}`, `/news/{symbol}`. All cached and reshaped.
- [x] Step 4 — Frontend shell (`static/index.html`, `static/style.css`, `static/app.js`):
      dark-themed watchlist with localStorage (capped at `MAX_FAVORITES = 10`, with
      an inline "watchlist is full" hint and disabled add controls when full), live
      prices from `/quote`, 90-day TradingView Lightweight Charts line chart from
      `/candles`. FastAPI serves the `static/` dir via `StaticFiles(html=True)`
      mounted at `/` in `main.py`.
- [x] Step 5 — Compare view (`static/compare.html`/`compare.js`: two-ticker
      side-by-side framework table from `/profile` + `/fundamentals`, plus
      `?a=&b=` deep-link prefill) and news view (`static/news.html`/`news.js`:
      ticker search + watchlist quick-chips, articles from `/news`).
- [x] Step 6 — Prompt library (`static/prompts.json` served directly through the
      `StaticFiles` mount — no backend dependency; `text` stored as an array of
      lines so multi-line prompts stay hand-editable without `\n` escaping;
      `static/prompts.html`/`prompts.js`: category-filter chips and
      copy-to-clipboard cards in the existing dark theme).

## Build order (suggested)
1. ~~FastAPI skeleton deployable to Render (one live endpoint).~~ **Done.**
2. ~~Data module + `/quote/{symbol}` end to end, with cache.~~ **Done.**
   - Hardening done: slowapi rate limiting + 24h candle cache (see Gotchas).
3. ~~Remaining endpoints: candles (yfinance), fundamentals, profile, news.~~ **Done.**
4. ~~Frontend shell + watchlist (localStorage) + one chart.~~ **Done.**
5. ~~Compare view, news view.~~ **Done.**
6. ~~Prompt library (static JSON + copy UI).~~ **Done.**

## Next steps (v2 — not started)
v1 is complete and hardened. v2 is designed-for but not built — see `docs/PLAN.md`
§ Versioning for full rationale:
- "Run this prompt for me" using the user's own API key (browser-side only)
- Auto-fill prompts with live fetched data
- Deeper fundamentals (possibly add FMP as a second provider)
- Real accounts for syncing favorites across devices

## Gotchas
- **Candles use yfinance — do not "fix" this.** Finnhub's free tier returns 403 for
  `stock/candle` on US equities; this is permanent. yfinance is the deliberate fallback
  for candles only. If it breaks, the chart returns an empty series (graceful); fix by
  paying for Finnhub candles or finding a new free source.
  Candles are cached for **24 hours** (completed daily closes are final and never change,
  so 24h is safe). The `/candles/{symbol}` endpoint is also rate-limited at **20/min**
  per IP via slowapi.
- `company_news` takes a date range; pass ~last 7 days, not a huge window.
- **`profile.marketCap` is in millions of USD** (Finnhub `marketCapitalization`,
  passed through unchanged by `get_profile`). AAPL ≈ `4514012` → $4.51T. When
  formatting for display, divide by `1_000_000` for trillions / `1_000` for
  billions — see `fmt()` in `static/compare.js` for the working tiered conversion.
- In-process dict cache is fine for v1 (vanishes on restart). Redis only if we ever
  run multiple instances.
- Secrets: the Finnhub API key is an env var on Render. Never commit it.
