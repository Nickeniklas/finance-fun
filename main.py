from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

load_dotenv()  # no-op on Render where the var is already in the environment

import data

app = FastAPI(title="Finance Fun API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/quote/{symbol}")
def quote(symbol: str):
    try:
        return data.get_quote(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail="Finnhub fetch failed")


@app.get("/candles/{symbol}")
def candles(symbol: str, days: int = 30):
    try:
        return data.get_candles(symbol, days)
    except Exception:
        raise HTTPException(status_code=502, detail="Finnhub fetch failed")


@app.get("/fundamentals/{symbol}")
def fundamentals(symbol: str):
    try:
        return data.get_fundamentals(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail="Finnhub fetch failed")


@app.get("/profile/{symbol}")
def profile(symbol: str):
    try:
        return data.get_profile(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail="Finnhub fetch failed")


@app.get("/news/{symbol}")
def news(symbol: str):
    try:
        return data.get_news(symbol)
    except Exception:
        raise HTTPException(status_code=502, detail="Finnhub fetch failed")
