import os
import time

import finnhub

_cache: dict = {}
_client: finnhub.Client | None = None

QUOTE_TTL = 30  # seconds — prices move; sub-minute refresh not needed for a glance


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


def get_quote(symbol: str) -> dict:
    symbol = symbol.upper()
    key = f"quote:{symbol}"

    hit = _cached(key, QUOTE_TTL)
    if hit is not None:
        return hit

    try:
        raw = _get_client().quote(symbol)
        result = {
            "symbol": symbol,
            "price": raw.get("c", 0),
            "change": raw.get("d", 0),
            "changePercent": raw.get("dp", 0),
            "high": raw.get("h", 0),
            "low": raw.get("l", 0),
            "previousClose": raw.get("pc", 0),
        }
        return _store(key, result)
    except Exception:
        stale = _cache.get(key)
        if stale:
            return stale["data"]
        raise
