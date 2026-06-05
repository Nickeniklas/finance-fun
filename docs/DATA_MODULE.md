# Data Module — Contract

The data module is the single layer between the app and external data providers.
Nothing else calls any data provider directly. It does three jobs: **fetch**,
**cache**, **reshape**.

Primary provider: **Finnhub** (`finnhub-python` client).
Candles exception: **yfinance** — see *Provider exceptions* below.

---

## Responsibilities

1. **Fetch** via the appropriate provider client (Finnhub for most; yfinance for candles).
2. **Cache** results in-process (a Python dict) with a per-data-type TTL, so repeat
   requests within the window don't re-hit any provider.
3. **Reshape** raw responses into clean, predictable objects so the frontend never sees
   provider-specific quirks (and so future provider swaps stay invisible to the frontend).
4. **Handle failure** — on any provider error or rate-limit, prefer serving
   slightly-stale cache; otherwise return a clean error. A hiccup must not crash a page.

---

## Feature → endpoint → cache map

| Feature | Provider | Call | Returns | Cache TTL | Why that TTL |
|---|---|---|---|---|---|
| Watchlist current price | Finnhub | `quote(symbol)` | price, day high/low, prev close, % change | 30 sec | Prices move constantly; sub-minute not needed for a glance |
| Watchlist line chart | **yfinance** | `Ticker(symbol).history(start, end)` | daily closes over a date range | 4 hours | Past closes never change |
| Compare — fundamentals | Finnhub | `company_basic_financials(symbol, 'all')` | P/E, margins, ROE, ratios | 12 hours | Fundamentals update quarterly at most |
| Compare — company info | Finnhub | `company_profile2(symbol)` | name, sector, industry, market cap | 24 hours | Effectively static |
| News (per ticker) | Finnhub | `company_news(symbol, from, to)` | recent articles for the ticker | 20 min | Updates through the day |
| (optional) General market news | Finnhub | `general_news('general')` | broad headlines | 20 min | Same |
| (optional) Peer suggestions | Finnhub | `company_peers(symbol)` | similar tickers | 24 hours | Rarely changes; nice for "compare vs peers" |

Core app touches only 4 endpoints: **quote, candles, basic financials, company news.**
Two optional ones (general news, peers) can come later.

---

## Caching pattern (identical for every type)

For any request:
1. Build a cache key, e.g. `quote:AAPL`, `candles:AAPL:30`, `news:AAPL`.
2. If a stored copy exists and is younger than that type's TTL → return it.
3. Otherwise fetch from the appropriate provider, store with a timestamp, return it.

One small helper does this for all data types; only the TTL differs. For v1 the cache
is a plain dict in the FastAPI process (vanishes on restart — fine). Reach for Redis
only later if running multiple instances or wanting cache to survive restarts.

**Why this keeps us safe on Finnhub's 60 calls/min:** the TTLs mean even with many
visitors we make at most a few Finnhub calls per ticker per minute. First visitor pays
the fetch; everyone else rides the cache. yfinance has no hard rate limit, but the same
caching discipline applies.

---

## Provider exceptions

### Candles: yfinance instead of Finnhub

**What happened:** Finnhub moved `stock/candle` off the free tier. Calling
`stock_candles()` for US equities now returns HTTP 403. This is permanent, not a bug.

**What we considered:**
- Alpha Vantage free tier: 25 requests/day — unusable for a public site.
- Paying for Finnhub: possible v2 option if yfinance becomes a problem.
- The original plan called for a strict single-provider policy behind the data module.

**Decision:** Use `yfinance` for candles only. Everything else (quote, fundamentals,
profile, news) stays on Finnhub. The data module boundary is preserved — nothing
outside `data.py` touches yfinance directly, same discipline as the Finnhub calls.

**Known risk:** yfinance is an unofficial Yahoo Finance scraper. Yahoo can break it
without notice. If that happens:
1. `get_candles()` will return an empty series (graceful degradation — chart shows
   nothing rather than crashing the page).
2. Short-term fix: serve stale cache if a cached series exists.
3. Long-term fix: pay for Finnhub candles, or defer charts until a free alternative
   appears.

---

## Endpoint specifics & gotchas

- **Candles (yfinance):** `yf.Ticker(symbol).history(start, end)` takes ISO date
  strings; `end` is exclusive. Pass `end=date.today()` to get through yesterday. The
  DataFrame index is a timezone-aware DatetimeIndex; call `.date().isoformat()` on each
  index entry for the `YYYY-MM-DD` string TradingView expects. The data module zips this
  into `{ time, value }` — frontend never sees the raw DataFrame.
- **The "today" point is intentionally excluded.** Completed daily closes are stable;
  a partial-day close would go stale fast. v1 decision: **charts show completed daily
  closes (through yesterday); the live price lives in the watchlist display, not the
  chart.** Keeps the 4-hour candle TTL safe.
- **News:** `company_news` takes a `from`/`to` date range. Pass ~last 7 days. Don't
  pass huge ranges — heavier call, more to cache.
- **Quote fields are terse** (`c` = current price, etc.) — reshape to named fields.

---

## Output shapes handed to the frontend (clean objects)

These are the contracts the frontend codes against. Exact field set can be refined,
but the shape stays clean and provider-agnostic.

```jsonc
// quote
{ "symbol": "AAPL", "price": 0, "change": 0, "changePercent": 0,
  "high": 0, "low": 0, "previousClose": 0 }

// candle series (for TradingView line/area)
{ "symbol": "AAPL",
  "series": [ { "time": "2026-01-02", "value": 0 }, /* ... */ ] }

// fundamentals (subset of basic financials, named)
{ "symbol": "AAPL", "peRatio": 0, "netMargin": 0, "roe": 0,
  "debtToEquity": 0, /* framework dimensions */ }

// company info
{ "symbol": "AAPL", "name": "", "sector": "", "industry": "", "marketCap": 0 }

// news item
{ "headline": "", "source": "", "url": "", "datetime": 0, "summary": "" }
```

---

## Comparison framework (dimensions for "compare stocks")

Normalize every ticker into the same schema so any 2+ slot into one table:
- **Valuation:** P/E, P/B, EV/EBITDA
- **Growth:** revenue growth, EPS growth
- **Profitability:** gross/net margin, ROE
- **Financial health:** debt/equity, current ratio
- **Price performance:** return over selected windows

Pull these from `company_basic_financials`. Whatever the free tier doesn't supply is a
v2/FMP gap — note it rather than blocking.
