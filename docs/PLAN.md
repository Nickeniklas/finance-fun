# Finance Tools — Project Plan

A public website for finance tools, visualizations, and a curated prompt library.
This document is the single source of truth for **what** we are building and **why**
the choices were made. It is written so that someone (human or Claude) reading it
cold understands the whole project.

---

## What this is

An open, public site (no login) offering:

1. **Compare stocks** — pull data for two or more tickers and show them side by side
   against a fixed comparison framework (valuation, growth, profitability, health).
2. **Finance news** — recent news, filterable by ticker.
3. **Favorite tickers** — a personal watchlist, saved in the browser, with a simple
   line chart of recent price history per ticker.
4. **Prompt library** — a curated, read-only collection of good finance/stock prompts
   the user can copy and paste into their own ChatGPT/Claude.

The site is for general public use. A core design goal is **no per-user inference
cost to us** — the prompt library works by the user copying prompts and running them
in their own AI tool, so they pay for their own inference.

---

## Versioning

### v1 (current scope)
- Compare stocks (data + framework)
- Finance news (by ticker)
- Favorite tickers (localStorage) + line chart
- Prompt library — standalone, copy-only, placeholders left for the user to fill
- No accounts, no database, no LLM calls from our side

### v2 (designed-for, not built yet)
- "Run this prompt for me" using the **user's own API key** (kept in their browser
  only, never stored server-side)
- Optionally auto-fill prompts with live fetched data
- Deeper fundamentals (possibly add FMP as a second data provider)
- Real accounts for syncing favorites across devices

The v1 design must not block any v2 item. Each v2 feature bolts on cleanly.

---

## Tech stack (all decided)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Vanilla HTML / CSS / JS | No framework. Owner does not write React. |
| Charts | TradingView Lightweight Charts | Plain JS, ~40kb, finance-native. Drawing only — no data fetching. |
| Backend | Python + FastAPI | Owner uses Python daily. |
| Hosting | Render (free tier) | Free tier, ~1-min cold start on idle; fine tradeoff for a low-traffic hobby site. |
| Data provider | Finnhub (free tier) + yfinance | Finnhub: 60 calls/min, quotes, news, fundamentals. yfinance: candles only (see rationale). |
| Favorites storage | Browser localStorage | No accounts, no DB in v1. |
| Prompt library storage | Static JSON file in repo | Read-only, authored by owner. |
| LLM | None in v1 | v2 uses user-supplied key, browser-side only. |

### Why these (short rationale)
- **Python/FastAPI over TypeScript/serverless:** fluency in Python beats the cheaper
  serverless tier for a side project. FastAPI feels familiar immediately.
- **Render (free tier):** Railway has no real free tier (trial credit only, ~$5/mo
  after). Render's free tier is genuinely free; the ~1-minute cold start on idle is an
  acceptable tradeoff for a low-traffic hobby site. The setup stays portable — the
  Procfile and `$PORT` convention work on Railway, Fly.io, or any other host too.
- **Finnhub over FMP/Alpha Vantage:** 60 calls/**minute** free beats FMP's 250/**day**.
  Covers quotes, news, and basic fundamentals. Limitation: deep historical fundamentals
  need a paid tier — revisit with FMP in v2 if needed.
- **yfinance for candles (deliberate exception):** Finnhub moved `stock/candle` off the
  free tier — it returns 403 for US equities. Alpha Vantage free is 25 requests/day,
  unusable for a public site. yfinance (unofficial Yahoo Finance scraper) fills the gap
  for candles only. The original plan called for strict single-provider discipline; we
  are consciously overriding that for this one data type. The data module boundary is
  preserved — nothing outside `data.py` touches yfinance. Known risk: Yahoo can break
  the scraper without notice; fallback is empty series (graceful) or paying for Finnhub
  candles. See `DATA_MODULE.md` for full detail.
- **localStorage over accounts:** the only feature wanting persistence is favorites.
  localStorage removes auth, a database, and a whole class of security concerns.
  Tradeoff accepted: favorites are per-device and don't sync (a v2 problem).
- **Standalone prompt library:** fully decoupled from the data layer. Lowest
  complexity. Auto-filling prompts with live data is a clean v2 add-on.

---

## Architecture overview

```
Browser (vanilla HTML/CSS/JS)
  ├── Watchlist UI ........ reads/writes favorites in localStorage
  ├── Charts .............. TradingView Lightweight Charts, fed clean arrays
  ├── Compare UI .......... renders side-by-side framework
  ├── News UI ............. renders article lists
  └── Prompt Library UI ... shows curated prompts, copy-to-clipboard
        │
        │  (HTTP/JSON)
        ▼
FastAPI backend (Render)
  └── Data module ......... the ONLY thing that talks to Finnhub or yfinance
        ├── in-process cache (Python dict) with per-type TTLs
        ├── reshapes Finnhub responses into clean objects
        └── handles rate limits / failures
        │
        ▼
Finnhub API (free tier)
```

Key boundary: **nothing except the data module calls any external data provider.**
This is what lets us swap/add providers, cache in one place, and keep API keys in
one place. Current providers: Finnhub (most data) + yfinance (candles — see rationale).

The prompt library is **standalone** — it does not touch the data layer at all in v1.

---

## Build status

1. ~~FastAPI skeleton deployable to Render ("hello world" endpoint live).~~ **Done.**
2. ~~Data module + one endpoint end to end (`/quote/{symbol}`), with cache.~~ **Done.**
3. ~~Remaining endpoints (candles via yfinance, fundamentals, profile, news).~~ **Done.**
4. Frontend shell + watchlist (localStorage) + one chart. **(next)**
5. Compare view, news view.
6. Prompt library (static JSON + copy UI).

See `DATA_MODULE.md` and `PROMPT_LIBRARY.md` for the detailed contracts.
