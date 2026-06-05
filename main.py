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
