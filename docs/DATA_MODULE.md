# Data Module — Contract

The data module is the single layer between the app and external data providers.
Nothing else calls any data provider directly. It does three jobs: **fetch**,
**cache**, **reshape**.

Primary provider: **Finnhub** (`finnhub-python` client), for US-listed tickers.
Candles, and any non-US/suffixed symbol (e.g. `NOKIA.HE`) for every data type: **yfinance**
— see *Provider exceptions* and *Non-US ticker support* below.

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
| Watchlist current price | Finnhub (US) / **yfinance** (non-US) | `quote(symbol)` / `Ticker(symbol).fast_info` | price, day high/low, prev close, % change, currency | 30 sec (Finnhub) / **5 min** (yfinance) | Prices move constantly; sub-minute not needed for a glance. yfinance gets a longer TTL to limit scraper load. |
| Watchlist line chart | **yfinance** (all symbols) | `Ticker(symbol).history(start, end)` | daily closes over a date range | 24 hours | Completed daily closes are final; 24h is safe |
| Compare — fundamentals | Finnhub (US) / **yfinance** (non-US) | `company_basic_financials(symbol, 'all')` / `Ticker(symbol).info` | P/E, margins, ROE, ratios | 12 hours | Fundamentals update quarterly at most |
| Compare — company info | Finnhub (US) / **yfinance** (non-US) | `company_profile2(symbol)` / `Ticker(symbol).info` | name, sector, industry, market cap, currency | 24 hours | Effectively static |
| News (per ticker) | Finnhub (US) / **yfinance** (non-US) | `company_news(symbol, from, to)` / `Ticker(symbol).news` | recent articles for the ticker | 20 min | Updates through the day |
| (optional) General market news | Finnhub | `general_news('general')` | broad headlines | 20 min | Same |
| (optional) Peer suggestions | Finnhub | `company_peers(symbol)` | similar tickers | 24 hours | Rarely changes; nice for "compare vs peers" |

"Non-US" means: the symbol (after alias normalization) contains a `.`, e.g.
`NOKIA.HE`. See *Non-US ticker support* below for the full routing rule.

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

## Non-US ticker support

**What happened:** Finnhub's free tier has **zero coverage outside US exchanges**.
A bare symbol like `NOKIA` returns an all-zero quote (not an error); a suffixed
symbol like `NOKIA.HE` returns a hard 403. yfinance, however, recognizes
exchange-suffixed symbols (`NOKIA.HE`, `FORTUM.HE`, `KNEBV.HE`, ...) and its
`fast_info` / `.info` / `.news` provide everything needed for quote, profile,
fundamentals, and news — not just candles.

**Decision:** Extend yfinance's role (previously candles-only) to also cover
quote/profile/fundamentals/news **for any symbol that, after normalization, contains
a `.`** (e.g. `NOKIA.HE`). Plain US tickers (`AAPL`, `MSFT`, ...) are unaffected and
keep using Finnhub.

**Symbol normalization (`data.py`):**
- `SYMBOL_ALIASES` is a flat dict mapping bare symbols a user would naturally type
  (`NOKIA`, `FORTUM`, `KNEBV`, and a starter set of other OMX Helsinki large-caps) to
  their Yahoo Finance symbol (`NOKIA.HE`, etc.).
- `_normalize_symbol(symbol)`: uppercase/strip; if the symbol already contains `.`,
  pass through unchanged (so `NOKIA.HE` typed directly works too); otherwise look up
  in `SYMBOL_ALIASES` (falls back to the symbol unchanged if not found).
- `_is_yfinance_routed(symbol)`: `"." in symbol` — the routing decision for
  quote/profile/fundamentals/news.
- The cache key uses the *normalized* symbol; the output `symbol` field always
  echoes the *user-requested* symbol (so `NOKIA` round-trips through localStorage
  and `?a=&b=` deep links, not `NOKIA.HE`).

**Reshaping yfinance → the same output contracts** (see `_fetch_*_yf` helpers):
- **Quote**: `fast_info` gives `lastPrice`, `previousClose`, `dayHigh`, `dayLow`,
  `currency`. `change`/`changePercent` are derived (`price - previousClose`, guarding
  divide-by-zero).
- **Profile**: `.info` gives `longName`, `sector`, `industry`, `marketCap` (raw
  units), `currency`.
- **Fundamentals**: `.info` fields need unit reconciliation to match Finnhub's
  conventions:
  - `revenueGrowth`, `earningsGrowth`, `grossMargins`, `profitMargins`,
    `returnOnEquity` are decimal fractions (0.05 = 5%) → **×100** to match Finnhub's
    percent numbers.
  - `debtToEquity` is a percent-like number (ratio×100) → **÷100** to match
    Finnhub's plain-ratio `totalDebt/totalEquityAnnual`.
  - `trailingPE` → `peRatio`, `priceToBook` → `pbRatio`,
    `enterpriseToEbitda` → `evEbitda`, `currentRatio` → `currentRatio` (no
    conversion needed for these).
- **News**: `.news` items nest data under `content` (`title`, `summary`,
  `provider.displayName`, `pubDate` as an ISO string, and a clickthrough URL under
  `canonicalUrl`/`clickThroughUrl`). `pubDate` is converted to a Unix timestamp via
  `_iso_to_unix()` to match Finnhub's `datetime` convention.

**Caching:** yfinance-routed quote calls use `QUOTE_TTL_YF = 5 min` (vs Finnhub's
30 sec) — quote is the only frequently-polled endpoint, so this is the main lever for
limiting yfinance scraper load from non-US symbols. Profile/fundamentals/news reuse
the existing TTLs (24h / 12h / 20min) — those are effectively static either way.

**Currency:** every quote and profile response now includes `"currency"`
(`"USD"` for Finnhub-routed responses, the instrument's native currency — e.g.
`"EUR"` — for yfinance-routed ones). The frontend formats prices and market caps with
`formatPrice()` / `fmt()` in `static/format.js` / `static/compare.js`.

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
  chart.** Keeps the 24-hour candle TTL safe.
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
  "high": 0, "low": 0, "previousClose": 0, "currency": "USD" }

// candle series (for TradingView line/area)
{ "symbol": "AAPL",
  "series": [ { "time": "2026-01-02", "value": 0 }, /* ... */ ] }

// fundamentals (subset of basic financials, named)
{ "symbol": "AAPL", "peRatio": 0, "netMargin": 0, "roe": 0,
  "debtToEquity": 0, /* framework dimensions */ }

// company info — marketCap is raw units in `currency` (not millions)
{ "symbol": "AAPL", "name": "", "sector": "", "industry": "",
  "marketCap": 0, "currency": "USD" }

// news item
{ "headline": "", "source": "", "url": "", "datetime": 0, "summary": "" }
```

For a non-US symbol (e.g. `NOKIA`), `symbol` echoes the user-requested form,
`currency` is `"EUR"`, and `marketCap` is in EUR.

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
