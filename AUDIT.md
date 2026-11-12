# Audit — finance-fun

Date: 2026-11-12 · Commit audited: `cdb75a5` (main, clean tree) · Read-only; this file is the only change.

Scope: every tracked source file (`data.py`, `main.py`, all `static/*.js` and `*.html`,
`routines/events-feed.md`, config, docs) plus git history for secrets. Findings marked
**Confirmed** were reproduced by calling `data.py` locally against the live providers;
anything else is labelled.

## 1. Top 5 findings (ranked by impact vs effort)

### 1. `days` on `/candles` is unbounded — cache bypass and memory exhaustion
**Where:** `main.py:47` (`days: int = 30`), `data.py:281` (cache key includes `days`), `data.py:287-289`.
**Status:** Confirmed.

Every distinct `days` value is a new cache key, so the 24h candle cache does not protect
Yahoo from a single client: `?days=91`, `?days=92`, … each trigger a fresh scrape.
Large values pull the full history: `get_candles("KO", 40000)` returned 16,325 rows
(675 KB of JSON) and was cached. The cache bounds entry *count* (500), not size, so
about a hundred such requests — five minutes at the 20/min limit — is likely enough to
exhaust a Render free instance (512 MB; the per-entry memory figure is my estimate, not
measured). Negative values (`days=-5`) are accepted and cache an empty series.

**Fix:** constrain it at the edge: `days: int = Query(30, ge=1, le=365)` in `main.py`,
or snap to a small allow-list (30/90/365) so the key space is fixed. The frontend only
ever sends 90.

### 2. An empty candle series is cached for 24 hours
**Where:** `data.py:297` (`_store(key, {"series": series})` runs even when `series == []`).
**Status:** Confirmed for unknown symbols and bad ranges; the Yahoo-block case is an inference (see §3).

yfinance usually reports failure by returning an empty DataFrame rather than raising.
That path skips the `except` block, so the "serve stale cache first" fallback at
`data.py:302-303` never runs — instead the empty result *overwrites* any good cached
series and is served for the next 24 hours. Given the documented Yahoo blocking of
Render's IP, one bad fetch blanks a ticker's chart for a day even after Yahoo recovers.

**Fix:** treat an empty series as a failure: if `series` is empty, return stale cache
if present, otherwise return `{"series": []}` without storing it (or store it with a
short TTL of a few minutes to avoid hammering Yahoo for genuinely unknown symbols).

### 3. Unknown or unsupported symbols return a fake `$0.00` quote with nulls that crash the watchlist
**Where:** `data.py:119-126`, `static/app.js:126` and `:181`, `static/format.js:36`.
**Status:** Backend confirmed; frontend crash traced by reading the code, not run in a browser.

Finnhub answers an unknown symbol with zeros and nulls instead of an error.
`get_quote("ZZZZQ")` returned `{"price": 0, "change": null, "changePercent": null, ...}`
with HTTP 200 — `raw.get("dp", 0)` does not default because the key exists with a null value.
Consequences:

- `quote.changePercent.toFixed(2)` throws on `null`. In `loadChart` (`app.js:181`) this
  happens before `drawChart` is reached, so the header switches to the new symbol at
  `$0.00` while the **previous ticker's chart stays on screen**. In `refreshPrice` the
  error is swallowed and the row just shows `$0.00`.
- A typo looks like a real stock priced at zero, and it can be added to the watchlist.
- The same happens for symbols the routing does not cover: `^GSPC` and `BTC-USD` pass
  validation, chart correctly via yfinance, but quote goes to Finnhub and returns zeros.

**Fix:** in `_fetch_quote_finnhub`, raise a "not found" error when `c == 0 and pc == 0`
(map it to a 404 in `main.py`) and use `raw.get("dp") or 0` for the nullable fields.
In `app.js`, guard the percent formatting so one bad field cannot skip `drawChart`.

### 4. Rate limiting probably keys on Render's proxy, not the visitor
**Where:** `main.py:14` (`get_remote_address`), start command in `README.md:94` / `Procfile`.
**Status:** Partly confirmed — the library behaviour is verified, Render's side is not.

slowapi's `get_remote_address` returns `request.client.host`. uvicorn only rewrites
that from `X-Forwarded-For` when the connecting peer is in `FORWARDED_ALLOW_IPS`, which
defaults to `127.0.0.1` (checked in the installed uvicorn). Behind Render's load
balancer the peer is not localhost, so unless Render sets that variable, every visitor
shares one bucket: the limits become site-wide (20 candle requests per minute for
everyone), one heavy client locks all users out, and per-IP abuse protection does not
exist.

**Fix:** first log `request.client.host` on Render to confirm. If it is the proxy
address, key the limiter on the left-most `X-Forwarded-For` entry via a custom
`key_func`, or start uvicorn with `--forwarded-allow-ips` set to Render's proxy range
(not `*` unless the app is unreachable except through the proxy, or the header becomes
spoofable).

### 5. The Events Feed publishes unattended LLM output to production with no machine check
**Where:** `routines/events-feed.md` §7 (self-merge to main), `static/events.js:11`, `:13`, `:16`, `:44`, `:80`.
**Status:** Confirmed by reading; no malformed file has been observed.

The routine web-searches, writes `events.json` / `digest.json`, validates them only by
its own judgement, and squash-merges its own PR. There is no CI (`.github/` does not
exist). Two weak points on the rendering side:

- `events.js:16` interpolates `theme.streak` into `innerHTML` without `escapeHtml` — the
  only unescaped JSON-sourced field on the page. Web content steering the routine into
  writing markup there would be stored XSS on the public site. Long chain, one-word fix.
- `renderDigest` / `renderDeal` assume `whatChanged`, `themes` and `phases` are arrays.
  One missing field throws inside the `try`, and the whole page falls back to
  "Couldn't load events" until the next daily run.

**Fix:** wrap `theme.streak` in `escapeHtml(Number(...))`. Add a small
`scripts/validate_events.py` implementing the six sanity rules already listed in
`docs/EVENTS_FEATURE.md`, have the routine run it, and run it as a required GitHub
Actions check so a bad file cannot be merged.

### Also noted (below the top 5)
- **US share classes with a dot are broken.** `_is_yfinance_routed` (`data.py:77-79`)
  sends any dotted symbol to Yahoo, but Yahoo spells `BRK.B` as `BRK-B`. Confirmed:
  `get_quote("BRK.B")` raises (`KeyError: 'exchangeTimezoneName'`, a 502) and candles
  come back empty. Fix: route on a set of known exchange suffixes, not on "contains a dot".
- **Unescaped symbols in `innerHTML`** at `static/news.js:44`, `:50`, `:73` and
  `static/app.js:104`. Input is the user's own typing or their own localStorage (10-char
  limit), so this is self-XSS only, but it breaks the repo's own escaping rule and
  `compare.js` already does it correctly.
- **No Subresource Integrity on the chart library** (`static/index.html:13`). The
  version is pinned, but a compromised unpkg response would run on the page; add
  `integrity` and `crossorigin`, or vendor the file into `static/`.
- **Cache eviction can race** (`data.py:93-97`): endpoints run in a threadpool, and two
  threads evicting at once can hit `KeyError` on `del`, which surfaces as a spurious 502.
  There is also no per-key lock, so concurrent misses each call the provider. Low
  likelihood at hobby traffic.

**Secrets:** nothing found. `.env` and `uvicorn.log` are ignored and were never tracked;
the current Finnhub key value appears in none of the 160 commits on any local ref, and a
pattern scan of history for key/token/secret assignments found only placeholders.
**Auth:** there is none by design (public, read-only), so there are no missing checks to report.

## 2. Tests that would catch real breakage

There are no tests in the repo. These five are the ones worth having; all mock the
providers, none need network access.

1. **Candle range bounds** (FastAPI `TestClient`): `days=0`, `-5`, `40000` and `abc`
   return 422 and create no cache entry; `days=90` returns 200. Guards finding 1.
2. **Candle failure handling**: with yfinance mocked to return an empty DataFrame, an
   existing cached series is still served and nothing empty is stored; with it mocked to
   raise, same result; a `NaN` close is dropped and the response is valid JSON. Guards
   finding 2 and the documented degradation contract.
3. **Unknown-symbol quote**: Finnhub mocked to return `{"c":0,"d":null,"dp":null,"pc":0,...}`
   yields a 404 (or at least no null numeric fields), and a provider exception with a
   warm cache yields the stale quote while a cold cache yields a 502 naming the right
   provider. Guards finding 3 and `_stale_or_raise`.
4. **Symbol validation and routing table**: parametrized over `NOKIA` → `NOKIA.HE` on
   yfinance, `AAPL` on Finnhub, `nokia.he`, `BRK.B`, `^GSPC`, and invalid inputs
   (`""`, `"AAPL;DROP"`, 11 characters) raising `ValueError` *before* any provider mock
   is called. Also assert the yfinance fundamentals unit conversion (fractions ×100,
   `debtToEquity` ÷100), which silently produces plausible but wrong numbers if a
   yfinance upgrade changes conventions.
5. **Events JSON schema check** run against the committed `static/events.json` and
   `static/digest.json`: required fields present, status values in the closed list,
   `currentStatus` equals the last phase's status, unique ids, date formats, `streak`
   is an integer. Run in CI on every PR. Guards finding 5.

## 3. Not verified

- **Render's proxy behaviour** (finding 4): I could not observe what `request.client.host`
  is in production or whether Render sets `FORWARDED_ALLOW_IPS`. The shared-bucket
  conclusion follows from uvicorn's defaults only.
- **How a Yahoo block presents** (finding 2): I saw empty series cached for an unknown
  symbol and a negative range. I did not reproduce a datacenter-IP block, so whether a
  block yields an empty DataFrame (bug applies) or an exception (stale path works) is an
  inference from yfinance's general behaviour.
- **Frontend behaviour** was traced by reading the JavaScript; nothing was run in a browser.
- **Memory impact** in finding 1 is an estimate from a measured row count, not a
  measured process size, and no load test was run.
- **Deployment and GitHub settings**: whether Render auto-deploys on push to main,
  whether main has branch protection, and what scope the routine's GitHub token has.
- **Secrets beyond the current key**: a previously rotated key, or commits on remote
  branches and PR refs not fetched locally, would not have been caught.
- **Dependency vulnerabilities**: no `pip-audit` or equivalent was run against
  `requirements.txt`.
- **Guess:** `fast_info` values can be `NaN`, which is truthy, so `info.get("lastPrice") or 0`
  (`data.py:132-133`) would pass it through; Starlette serializes with `allow_nan=False`,
  so that would be a 500 served from cache for five minutes. Not observed.
- **Guess:** if yfinance ever returns a non-numeric fundamental (for example the string
  `"Infinity"` for a P/E), `fmt()` in `static/compare.js:17-27` would throw on `.toFixed`
  and leave the page on "Loading…". Not observed.
- Not reviewed: `static/style.css`, image assets, and the factual accuracy of the events content.

The live probes made about ten real provider calls with the local `.env` key; nothing
was written outside this file and a scratch script in the session temp directory.
