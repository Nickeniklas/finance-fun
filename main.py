from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()  # no-op on Render where the var is already in the environment

import data

app = FastAPI(title="Finance Fun API")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
def health():
    return {"status": "ok"}


# Endpoints route to Finnhub or yfinance per-symbol inside data.py, so the error
# detail stays provider-agnostic rather than naming a specific provider.
_UPSTREAM_ERROR = "upstream data fetch failed"


@app.get("/quote/{symbol}")
@limiter.limit("60/minute")
def quote(request: Request, symbol: str):
    try:
        return data.get_quote(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail=_UPSTREAM_ERROR)


@app.get("/candles/{symbol}")
@limiter.limit("20/minute")
def candles(request: Request, symbol: str, days: int = 30):
    # get_candles degrades to an empty series rather than raising (see DATA_MODULE.md),
    # so this never 502s — the handler stays only as a defensive backstop.
    return data.get_candles(symbol, days)


@app.get("/fundamentals/{symbol}")
@limiter.limit("60/minute")
def fundamentals(request: Request, symbol: str):
    try:
        return data.get_fundamentals(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail=_UPSTREAM_ERROR)


@app.get("/profile/{symbol}")
@limiter.limit("60/minute")
def profile(request: Request, symbol: str):
    try:
        return data.get_profile(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail=_UPSTREAM_ERROR)


@app.get("/news/{symbol}")
@limiter.limit("60/minute")
def news(request: Request, symbol: str):
    try:
        return data.get_news(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail=_UPSTREAM_ERROR)


# Static files must be mounted last so API routes take priority
app.mount("/", StaticFiles(directory="static", html=True), name="static")
