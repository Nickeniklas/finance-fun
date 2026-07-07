import os
import re
import time
from datetime import date, datetime, timedelta

import finnhub
import yfinance as yf
from curl_cffi import requests as curl_requests

_cache: dict = {}
_client: finnhub.Client | None = None

# Public input is arbitrary and unauthenticated, so the cache is bounded: once it
# exceeds this size, evict the oldest entries (by stored timestamp) down to a lower
# watermark, rather than evicting on every single insert.
_CACHE_MAX_SIZE = 500
_CACHE_EVICT_TO = 400

_SYMBOL_RE = re.compile(r"^[A-Z0-9.^-]{1,10}$")

# Reused browser-impersonation session for all yfinance calls. yfinance runs on
# Render's datacenter IP, which Yahoo rate-limits/blocks aggressively; a curl_cffi
# Chrome-impersonation session reduces (but does not eliminate) that blocking.
_yf_session = curl_requests.Session(impersonate="chrome")

QUOTE_TTL = 30             # seconds
QUOTE_TTL_YF = 5 * 60      # yfinance-routed quotes: longer TTL, limits scraper load
CANDLE_TTL = 24 * 3600     # completed daily closes never change; 24h is safe
FUNDAMENTALS_TTL = 12 * 3600
PROFILE_TTL = 24 * 3600
NEWS_TTL = 20 * 60

# Bare non-US symbols (e.g. "NOKIA") need their Yahoo Finance exchange suffix
# (e.g. "NOKIA.HE") for yfinance to recognize them. Symbols that already contain "."
# pass through unchanged. Finnhub's free tier has zero coverage for these exchanges,
# so any suffixed symbol routes quote/profile/fundamentals/news to yfinance too.
SYMBOL_ALIASES = {
    "NOKIA": "NOKIA.HE",
    "FORTUM": "FORTUM.HE",
    "KNEBV": "KNEBV.HE",    # KONE
    "SAMPO": "SAMPO.HE",
    "NESTE": "NESTE.HE",
    "UPM": "UPM.HE",
    "STERV": "STERV.HE",    # Stora Enso
    "ELISA": "ELISA.HE",
    "ORNBV": "ORNBV.HE",    # Orion B
    "WRT1V": "WRT1V.HE",    # Wartsila
    "TIETO": "TIETO.HE",    # TietoEVRY
    "OUT1V": "OUT1V.HE",    # Outokumpu
    "METSO": "METSO.HE",
    "KESKOB": "KESKOB.HE",  # Kesko B
    "MOCORP": "MOCORP.HE",  # Metsa Board
}


def _get_client() -> finnhub.Client:
    global _client
    if _client is None:
        _client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    return _client


def _validate_symbol(symbol: str) -> str:
    upper = symbol.upper().strip()
    if not _SYMBOL_RE.match(upper):
        raise ValueError(f"Invalid ticker symbol: {symbol!r}")
    return upper


def _normalize_symbol(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if "." in symbol:
        return symbol
    return SYMBOL_ALIASES.get(symbol, symbol)


def _is_yfinance_routed(symbol: str) -> bool:
    # Suffixed symbols (e.g. "NOKIA.HE") have no Finnhub free-tier coverage.
    return "." in symbol


def _iso_to_unix(iso_str: str) -> int:
    return int(datetime.fromisoformat(iso_str.replace("Z", "+00:00")).timestamp())


def _cached(key: str, ttl: int):
    entry = _cache.get(key)
    if entry and (time.time() - entry["at"]) < ttl:
        return entry["data"]
    return None


def _evict_if_needed():
    if len(_cache) > _CACHE_MAX_SIZE:
        oldest_first = sorted(_cache.items(), key=lambda kv: kv[1]["at"])
        for key, _ in oldest_first[: len(_cache) - _CACHE_EVICT_TO]:
            del _cache[key]


def _store(key: str, value):
    _cache[key] = {"data": value, "at": time.time()}
    _evict_if_needed()
    return value


def _stale_or_raise(key: str, exc: Exception):
    stale = _cache.get(key)
    if stale:
        return stale["data"]
    raise exc


# ---------------------------------------------------------------------------
# Provider fetchers (return data without the "symbol" field — callers add it)
# ---------------------------------------------------------------------------

def _fetch_quote_finnhub(symbol: str) -> dict:
    raw = _get_client().quote(symbol)
    return {
        "price": raw.get("c", 0),
        "change": raw.get("d", 0),
        "changePercent": raw.get("dp", 0),
        "high": raw.get("h", 0),
        "low": raw.get("l", 0),
        "previousClose": raw.get("pc", 0),
        "currency": "USD",
    }


def _fetch_quote_yf(symbol: str) -> dict:
    info = yf.Ticker(symbol, session=_yf_session).fast_info
    price = info.get("lastPrice") or 0
    previous_close = info.get("previousClose") or 0
    change = price - previous_close
    change_percent = (change / previous_close * 100) if previous_close else 0
    return {
        "price": price,
        "change": change,
        "changePercent": change_percent,
        "high": info.get("dayHigh") or 0,
        "low": info.get("dayLow") or 0,
        "previousClose": previous_close,
        "currency": info.get("currency"),
    }


def _fetch_profile_finnhub(symbol: str) -> dict:
    raw = _get_client().company_profile2(symbol=symbol)
    market_cap = raw.get("marketCapitalization")
    return {
        "name": raw.get("name"),
        # Finnhub's free profile has no separate sector field — only industry is real.
        "industry": raw.get("finnhubIndustry"),
        # Finnhub returns marketCapitalization in millions of USD; normalize to raw
        # units so the field is provider-agnostic (yfinance returns raw units).
        "marketCap": market_cap * 1_000_000 if market_cap is not None else None,
        "currency": "USD",
    }


def _fetch_profile_yf(symbol: str) -> dict:
    info = yf.Ticker(symbol, session=_yf_session).info
    return {
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "marketCap": info.get("marketCap"),
        "currency": info.get("currency"),
    }


def _fetch_fundamentals_finnhub(symbol: str) -> dict:
    raw = _get_client().company_basic_financials(symbol, "all")
    m = raw.get("metric", {})
    return {
        # Valuation
        "peRatio": m.get("peTTM"),
        "pbRatio": m.get("pbAnnual"),
        "evEbitda": m.get("evEbitdaTTM"),
        # Growth
        "revenueGrowthYoy": m.get("revenueGrowthTTMYoy"),
        "epsGrowthYoy": m.get("epsGrowthTTMYoy"),
        # Profitability
        "grossMargin": m.get("grossMarginTTM"),
        "netMargin": m.get("netProfitMarginTTM"),
        "roe": m.get("roeTTM"),
        # Financial health
        "currentRatio": m.get("currentRatioAnnual"),
        "debtToEquity": m.get("totalDebt/totalEquityAnnual"),
    }


def _fetch_fundamentals_yf(symbol: str) -> dict:
    info = yf.Ticker(symbol, session=_yf_session).info

    def pct(key):
        # yfinance gives growth/margin/ROE as decimal fractions (0.05 = 5%);
        # Finnhub gives them as percent numbers already (5.0) — scale to match.
        value = info.get(key)
        return value * 100 if value is not None else None

    debt_to_equity = info.get("debtToEquity")
    return {
        "peRatio": info.get("trailingPE"),
        "pbRatio": info.get("priceToBook"),
        "evEbitda": info.get("enterpriseToEbitda"),
        "revenueGrowthYoy": pct("revenueGrowth"),
        "epsGrowthYoy": pct("earningsGrowth"),
        "grossMargin": pct("grossMargins"),
        "netMargin": pct("profitMargins"),
        "roe": pct("returnOnEquity"),
        "currentRatio": info.get("currentRatio"),
        # yfinance's debtToEquity is a percent-like number (ratio * 100); Finnhub's
        # totalDebt/totalEquityAnnual is a plain ratio — divide to match Finnhub.
        "debtToEquity": debt_to_equity / 100 if debt_to_equity is not None else None,
    }


def _fetch_news_finnhub(symbol: str) -> list[dict]:
    today = date.today()
    from_date = (today - timedelta(days=7)).isoformat()
    to_date = today.isoformat()
    raw = _get_client().company_news(symbol, _from=from_date, to=to_date)
    return [
        {
            "headline": item.get("headline"),
            "source": item.get("source"),
            "url": item.get("url"),
            "datetime": item.get("datetime"),
            "summary": item.get("summary"),
        }
        for item in (raw or [])
    ]


def _fetch_news_yf(symbol: str) -> list[dict]:
    raw = yf.Ticker(symbol, session=_yf_session).news
    result = []
    for item in (raw or []):
        content = item.get("content") or {}
        provider = content.get("provider") or {}
        url = (
            (content.get("canonicalUrl") or {}).get("url")
            or (content.get("clickThroughUrl") or {}).get("url")
            or ""
        )
        pub_date = content.get("pubDate")
        result.append({
            "headline": content.get("title"),
            "source": provider.get("displayName"),
            "url": url,
            "datetime": _iso_to_unix(pub_date) if pub_date else 0,
            "summary": content.get("summary"),
        })
    return result


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def get_quote(symbol: str) -> dict:
    requested = _validate_symbol(symbol)
    norm = _normalize_symbol(requested)
    yf_routed = _is_yfinance_routed(norm)
    key = f"quote:{norm}"
    ttl = QUOTE_TTL_YF if yf_routed else QUOTE_TTL
    hit = _cached(key, ttl)
    if hit is None:
        try:
            data = _fetch_quote_yf(norm) if yf_routed else _fetch_quote_finnhub(norm)
            hit = _store(key, data)
        except Exception as e:
            hit = _stale_or_raise(key, e)
    return {**hit, "symbol": requested}


def get_candles(symbol: str, days: int = 30) -> dict:
    requested = _validate_symbol(symbol)
    norm = _normalize_symbol(requested)
    key = f"candles:{norm}:{days}"
    hit = _cached(key, CANDLE_TTL)
    if hit is None:
        try:
            # Charts show completed daily closes through yesterday — no partial-day point.
            # yfinance end date is exclusive, so passing today gives us through yesterday.
            start = (date.today() - timedelta(days=days)).isoformat()
            end = date.today().isoformat()
            history = yf.Ticker(norm, session=_yf_session).history(start=start, end=end)
            series = [
                {"time": idx.date().isoformat(), "value": round(row["Close"], 4)}
                for idx, row in history.iterrows()
                # Yahoo occasionally returns a NaN close for the most recent bar;
                # NaN serializes to invalid JSON and would break the chart, so skip it.
                if row["Close"] == row["Close"]  # False only for NaN
            ]
            hit = _store(key, {"series": series})
        except Exception:
            # Candles are the documented exception (see DATA_MODULE.md): a provider
            # failure must degrade to an empty series, never crash the page. Serve
            # stale cache if we have any, otherwise an empty series.
            stale = _cache.get(key)
            hit = stale["data"] if stale else {"series": []}
    return {**hit, "symbol": requested}


def get_fundamentals(symbol: str) -> dict:
    requested = _validate_symbol(symbol)
    norm = _normalize_symbol(requested)
    yf_routed = _is_yfinance_routed(norm)
    key = f"fundamentals:{norm}"
    hit = _cached(key, FUNDAMENTALS_TTL)
    if hit is None:
        try:
            data = _fetch_fundamentals_yf(norm) if yf_routed else _fetch_fundamentals_finnhub(norm)
            hit = _store(key, data)
        except Exception as e:
            hit = _stale_or_raise(key, e)
    return {**hit, "symbol": requested}


def get_profile(symbol: str) -> dict:
    requested = _validate_symbol(symbol)
    norm = _normalize_symbol(requested)
    yf_routed = _is_yfinance_routed(norm)
    key = f"profile:{norm}"
    hit = _cached(key, PROFILE_TTL)
    if hit is None:
        try:
            data = _fetch_profile_yf(norm) if yf_routed else _fetch_profile_finnhub(norm)
            hit = _store(key, data)
        except Exception as e:
            hit = _stale_or_raise(key, e)
    return {**hit, "symbol": requested}


def get_news(symbol: str) -> list[dict]:
    requested = _validate_symbol(symbol)
    norm = _normalize_symbol(requested)
    yf_routed = _is_yfinance_routed(norm)
    key = f"news:{norm}"
    hit = _cached(key, NEWS_TTL)
    if hit is not None:
        return hit
    try:
        result = _fetch_news_yf(norm) if yf_routed else _fetch_news_finnhub(norm)
        return _store(key, result)
    except Exception as e:
        return _stale_or_raise(key, e)
