import os
import time
from datetime import date, timedelta

import finnhub
import yfinance as yf

_cache: dict = {}
_client: finnhub.Client | None = None

QUOTE_TTL = 30             # seconds
CANDLE_TTL = 4 * 3600      # past closes don't change; 4 h is generous
FUNDAMENTALS_TTL = 12 * 3600
PROFILE_TTL = 24 * 3600
NEWS_TTL = 20 * 60


def _get_client() -> finnhub.Client:
    global _client
    if _client is None:
        _client = finnhub.Client(api_key=os.environ["FINNHUB_API_KEY"])
    return _client


def _cached(key: str, ttl: int):
    entry = _cache.get(key)
    if entry and (time.time() - entry["at"]) < ttl:
        return entry["data"]
    return None


def _store(key: str, value):
    _cache[key] = {"data": value, "at": time.time()}
    return value


def _stale_or_raise(key: str, exc: Exception):
    stale = _cache.get(key)
    if stale:
        return stale["data"]
    raise exc


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def get_quote(symbol: str) -> dict:
    symbol = symbol.upper()
    key = f"quote:{symbol}"
    hit = _cached(key, QUOTE_TTL)
    if hit is not None:
        return hit
    try:
        raw = _get_client().quote(symbol)
        return _store(key, {
            "symbol": symbol,
            "price": raw.get("c", 0),
            "change": raw.get("d", 0),
            "changePercent": raw.get("dp", 0),
            "high": raw.get("h", 0),
            "low": raw.get("l", 0),
            "previousClose": raw.get("pc", 0),
        })
    except Exception as e:
        return _stale_or_raise(key, e)


def get_candles(symbol: str, days: int = 30) -> dict:
    symbol = symbol.upper()
    key = f"candles:{symbol}:{days}"
    hit = _cached(key, CANDLE_TTL)
    if hit is not None:
        return hit
    try:
        # Charts show completed daily closes through yesterday — no partial-day point.
        # yfinance end date is exclusive, so passing today gives us through yesterday.
        start = (date.today() - timedelta(days=days)).isoformat()
        end = date.today().isoformat()
        hist = yf.Ticker(symbol).history(start=start, end=end)
        series = [
            {"time": idx.date().isoformat(), "value": round(row["Close"], 4)}
            for idx, row in hist.iterrows()
        ]
        return _store(key, {"symbol": symbol, "series": series})
    except Exception as e:
        return _stale_or_raise(key, e)


def get_fundamentals(symbol: str) -> dict:
    symbol = symbol.upper()
    key = f"fundamentals:{symbol}"
    hit = _cached(key, FUNDAMENTALS_TTL)
    if hit is not None:
        return hit
    try:
        raw = _get_client().company_basic_financials(symbol, "all")
        m = raw.get("metric", {})
        return _store(key, {
            "symbol": symbol,
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
        })
    except Exception as e:
        return _stale_or_raise(key, e)


def get_profile(symbol: str) -> dict:
    symbol = symbol.upper()
    key = f"profile:{symbol}"
    hit = _cached(key, PROFILE_TTL)
    if hit is not None:
        return hit
    try:
        raw = _get_client().company_profile2(symbol=symbol)
        return _store(key, {
            "symbol": symbol,
            "name": raw.get("name"),
            "sector": raw.get("finnhubIndustry"),   # Finnhub has no separate sector field
            "industry": raw.get("finnhubIndustry"),
            "marketCap": raw.get("marketCapitalization"),
        })
    except Exception as e:
        return _stale_or_raise(key, e)


def get_news(symbol: str) -> list[dict]:
    symbol = symbol.upper()
    key = f"news:{symbol}"
    hit = _cached(key, NEWS_TTL)
    if hit is not None:
        return hit
    try:
        today = date.today()
        from_date = (today - timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        raw = _get_client().company_news(symbol, _from=from_date, to=to_date)
        result = [
            {
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url"),
                "datetime": item.get("datetime"),
                "summary": item.get("summary"),
            }
            for item in (raw or [])
        ]
        return _store(key, result)
    except Exception as e:
        return _stale_or_raise(key, e)
