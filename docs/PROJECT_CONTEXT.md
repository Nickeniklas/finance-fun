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
| Quote, news, fundamentals, profile — **US-listed tickers** | **Finnhub** (free tier, 60 calls/min) | Primary provider |
| Daily candle history — **all tickers** | **yfinance** | Deliberate exception — see below |
| Quote, news, fundamentals, profile — **non-US/suffixed tickers** (e.g. `NOKIA.HE`) | **yfinance** | Finnhub free tier has zero coverage outside US exchanges — see below |

**Candles use yfinance by design.** Finnhub moved `stock/candle` off the free tier;
it returns 403 for US equities. This is permanent. Alpha Vantage free (25 req/day) is
unusable for a public site. yfinance fills the gap for candles only. The data module
boundary is preserved — nothing outside `data.py` touches either provider. If yfinance
breaks, the chart endpoint returns an empty series rather than crashing. Candles are
cached 24h (completed daily closes are final); the `/candles` endpoint is rate-limited
at 20/min per IP via slowapi.

**Non-US tickers (e.g. Finnish stocks: NOKIA, FORTUM, KNEBV) route through yfinance
for everything**, not just candles — Finnhub's free tier has no data for these
exchanges at all (zero quote, 403 on profile/fundamentals/news). `data.py` maps bare
symbols to their Yahoo suffix (`NOKIA` → `NOKIA.HE`) via `SYMBOL_ALIASES`; any
suffixed symbol routes to yfinance. Quote/profile responses include a `currency`
field (`"USD"` or the instrument's native currency, e.g. `"EUR"`); `marketCap` is raw
units in that currency for both providers. yfinance-routed quotes use a 5-minute
cache (vs Finnhub's 30s) to limit scraper load. See `DATA_MODULE.md` § Non-US ticker
support for full detail.

## Build status

**v1 complete and hardened, plus non-US ticker support (Finnish/OMX Helsinki via
yfinance routing).** v2 is designed-for but not started. See the status summary in
[`../README.md`](../README.md) and v2 scope in [`PLAN.md`](PLAN.md) § Versioning.

## Hard constraints (do not re-litigate without asking)

- Vanilla HTML/CSS/JS frontend — owner does not write React
- No accounts, no database, no server-side LLM calls in v1
- All provider calls go through `data.py` — frontend never calls Finnhub or yfinance
- Cache every external call (TTLs in `DATA_MODULE.md`)
- Data endpoints are rate-limited via slowapi (candles 20/min, others 60/min) to
  protect the unofficial yfinance scraping from symbol-enumeration abuse
- Finnhub API key lives only in Render's environment variables — never in code
