import os

from fastapi import FastAPI

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

app = FastAPI(title="Finance Fun API")


@app.get("/health")
def health():
    return {"status": "ok"}
