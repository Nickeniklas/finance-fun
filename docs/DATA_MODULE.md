# Data Module — Contract

The data module is the single layer between the app and Finnhub. Nothing else calls
Finnhub directly. It does three jobs: **fetch**, **cache**, **reshape**.

Use the official `finnhub-python` client rather than hand-writing HTTP calls.

---

## Responsibilities

1. **Fetch** via the Finnhub client.
2. **Cache** results in-process (a Python dict) with a per-data-type TTL, so repeat
   requests within the window don't re-hit Finnhub.
3. **Reshape** Finnhub's terse responses into clean, predictable objects so the
   frontend never sees Finnhub's quirks (and so a provider swap stays invisible).
4. **Handle failure** — on a Finnhub error or rate-limit (429), prefer serving
   slightly-stale cache; otherwise return a clean error. A hiccup must not crash a page.

---

## Feature → endpoint → cache map

| Feature | Finnhub client call | Returns | Cache TTL | Why that TTL |
|---|---|---|---|---|
| Watchlist current price | `quote(symbol)` | price, day high/low, prev close, % change | 30–60 sec | Prices move constantly; sub-minute not needed for a glance |
| Watchlist line chart | `stock_candles(symbol, 'D', from, to)` | daily OHLC over a range | a few hours | Past closes never change |
| Compare — fundamentals | `company_basic_financials(symbol, 'all')` | P/E, margins, ROE, ratios | 12–24 hours | Fundamentals update quarterly at most |
| Compare — company info | `company_profile2(symbol)` | name, sector, industry, market cap | 24 hours | Effectively static |
| News (per ticker) | `company_news(symbol, from, to)` | recent articles for the ticker | 15–30 min | Updates through the day |
| (optional) General market news | `general_news('general')` | broad headlines | 15–30 min | Same |
| (optional) Peer suggestions | `company_peers(symbol)` | similar tickers | 24 hours | Rarely changes; nice for "compare vs peers" |

Core app touches only 4 endpoints: **quote, candles, basic financials, company news.**
Two optional ones (general news, peers) can come later.

---

## Caching pattern (identical for every type)

For any request:
1. Build a cache key, e.g. `quote:AAPL`, `candles:AAPL:30d`, `news:AAPL`.
2. If a stored copy exists and is younger than that type's TTL → return it.
3. Otherwise fetch from Finnhub, store with a timestamp, return it.

One small helper does this for all rows above; only the TTL differs. For v1 the cache
is a plain dict in the FastAPI process (vanishes on restart — fine). Reach for Redis
only later if running multiple instances or wanting cache to survive restarts.

**Why this keeps us safe on 60 calls/min:** the TTLs mean even with many visitors we
make at most a few calls per ticker per minute. First visitor pays the fetch; everyone
else rides the cache. Cache each symbol independently so overlapping favorites across
visitors share hits.

---

## Endpoint specifics & gotchas

- **Candles:** `from`/`to` are **UNIX timestamps**. "X-day chart" = now back to X days
  ago. The client returns parallel arrays (`c` closes, `t` timestamps). Zip them into
  `{ time, value }` (time as `YYYY-MM-DD` or UNIX) for TradingView. This zip is the
  data module's job — frontend never sees the array form.
- **The "today" point is the only awkward bit.** Historical closes are frozen, but a
  live partial-day point goes stale fast. v1 decision: **charts show completed daily
  closes (through yesterday); the live price lives in the watchlist display, not the
  chart.** Keeps the candle TTL comfortably long.
- **News:** `company_news` takes a `from`/`to` date range. For "recent news" pass ~last
  7 days. Don't pass huge ranges — heavier call, more to cache.
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
