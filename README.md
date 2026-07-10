# finance-fun

A public (no-login) finance site. Compare stocks, read finance news, track favorite
tickers with a price chart, and browse a curated prompt library.

See [`docs/PLAN.md`](docs/PLAN.md) for the full project plan and rationale.

---

## Current status

**v1 complete and hardened.** FastAPI backend + full data layer and the whole frontend
(watchlist with chart, compare view, news view, prompt library), plus slowapi rate
limiting, a 24h candle cache, and non-US ticker support (Finnish/OMX Helsinki tickers
like NOKIA, FORTUM, KNEBV via yfinance routing with currency-aware display).

v2 — own-key prompts, deeper fundamentals, real accounts — is designed-for but not
started. See [`docs/PLAN.md`](docs/PLAN.md) § Versioning.

**Events Feed (standalone content + new frontend tab):** a daily content routine
([`routines/events-feed.md`](routines/events-feed.md)) web-searches for material
company M&A/partnership/capital-allocation news and maintains
[`static/events.json`](static/events.json) (append-only deal records) and
[`static/digest.json`](static/digest.json) (daily delta + themes snapshot). Schema is
locked in [`docs/EVENTS_FEATURE.md`](docs/EVENTS_FEATURE.md). It's independent of the
Finnhub/yfinance data layer. **`/events.html`** now renders both files directly (no API
endpoint — plain `fetch` of the static JSON): the digest (what changed + themes) up
top, then each tracked deal with its full phase history and current status. Linked from
the header nav on every page.

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Vanilla HTML / CSS / JS |
| Charts | TradingView Lightweight Charts |
| Backend | Python + FastAPI |
| Hosting | Render (free tier) |
| Data | Finnhub free tier (quotes, news, fundamentals, profile — US tickers) + yfinance 1.4.1 (candles for all tickers, 24h cache; quotes/news/fundamentals/profile for non-US/suffixed tickers; calls go through a curl_cffi Chrome-impersonation session to reduce datacenter-IP blocking) |
| Rate limiting | slowapi — candles 20/min, other data endpoints 60/min (per IP) |
| Favorites | Browser localStorage |
| Prompt library | Static JSON in repo |

---

## Data flow

![data flow diagram](docs/finance_fun_request_lifecycle.svg)

---

## Local development

```powershell
# First time only
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Add your Finnhub key (never commit this file)
# Create .env in the repo root:
#   FINNHUB_API_KEY=your_key_here

# Start the dev server
.\.venv\Scripts\uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000` — the watchlist + chart frontend loads directly.
Other pages: `/compare.html` (two-ticker comparison, with watchlist quick-chips to
fill either side), `/news.html` (ticker news search + watchlist quick-chips),
`/events.html` (Events Feed digest + tracked deals, reads the static JSON files
directly), `/prompts.html` (prompt library, copy-to-clipboard); all linked from the
header nav.

API endpoints: `/quote/AAPL`, `/candles/AAPL?days=30`, `/fundamentals/AAPL`,
`/profile/AAPL`, `/news/AAPL`. Health check: `/health`.

Non-US tickers like `NOKIA`, `FORTUM`, `KNEBV` (and any `SYMBOL.HE`-style suffixed
symbol) are supported via yfinance routing — see
[`docs/DATA_MODULE.md`](docs/DATA_MODULE.md) § Non-US ticker support.

**VS Code:** select `.venv/Scripts/python.exe` as the Python interpreter
(`Ctrl+Shift+P → Python: Select Interpreter`).

---

## Render deployment

1. Push to GitHub.
2. In [Render](https://render.com) → **New → Web Service** → connect your repo.
3. Set these in the Render dashboard:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment** → add `FINNHUB_API_KEY` with your key.
5. Deploy — Render assigns a public URL automatically.

**Never commit the API key** — it must live only in Render's environment variables.

> Free-tier services spin down after ~15 min of inactivity and take ~1 min to wake on
> the next request. This is fine for a low-traffic hobby site.

---

## Docs

| File | Contents |
|---|---|
| [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | Quick orient: build status, two-provider design, hard constraints |
| [`docs/PLAN.md`](docs/PLAN.md) | Full project plan, stack rationale, architecture |
| [`docs/DATA_MODULE.md`](docs/DATA_MODULE.md) | Data module contract: endpoints, cache TTLs, provider exceptions, output shapes |
| [`docs/PROMPT_LIBRARY.md`](docs/PROMPT_LIBRARY.md) | Prompt library contract: record shape, frontend behaviour |
| [`docs/EVENTS_FEATURE.md`](docs/EVENTS_FEATURE.md) | Events Feed contract: deal/digest record shapes, status lifecycle, validation rules |
| [`CLAUDE.md`](CLAUDE.md) | Operating brief for Claude Code |
