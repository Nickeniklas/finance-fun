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


def _provider_label(symbol: str) -> str:
    # Routing (Finnhub vs yfinance) is decided per-symbol in data.py, so the error
    # message names whichever provider actually served (or failed to serve) this symbol.
    try:
        norm = data._normalize_symbol(symbol.upper().strip())
    except Exception:
        return "Finnhub"
    return "yfinance" if data._is_yfinance_routed(norm) else "Finnhub"


@app.get("/quote/{symbol}")
@limiter.limit("60/minute")
def quote(request: Request, symbol: str):
    try:
        return data.get_quote(symbol)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")
    except Exception:
        raise HTTPException(status_code=502, detail=f"Quote fetch failed ({_provider_label(symbol)})")


@app.get("/candles/{symbol}")
@limiter.limit("20/minute")
def candles(request: Request, symbol: str, days: int = 30):
    try:
        # get_candles degrades to an empty series rather than raising (see
        # DATA_MODULE.md) for provider errors, so this only ever raises on a
        # malformed symbol.
        return data.get_candles(symbol, days)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")


@app.get("/fundamentals/{symbol}")
@limiter.limit("60/minute")
def fundamentals(request: Request, symbol: str):
    try:
        return data.get_fundamentals(symbol)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")
    except Exception:
        raise HTTPException(status_code=502, detail=f"Fundamentals fetch failed ({_provider_label(symbol)})")


@app.get("/profile/{symbol}")
@limiter.limit("60/minute")
def profile(request: Request, symbol: str):
    try:
        return data.get_profile(symbol)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")
    except Exception:
        raise HTTPException(status_code=502, detail=f"Profile fetch failed ({_provider_label(symbol)})")


@app.get("/news/{symbol}")
@limiter.limit("60/minute")
def news(request: Request, symbol: str):
    try:
        return data.get_news(symbol)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid ticker symbol")
    except Exception:
        raise HTTPException(status_code=502, detail=f"News fetch failed ({_provider_label(symbol)})")


# Static files must be mounted last so API routes take priority
app.mount("/", StaticFiles(directory="static", html=True), name="static")
