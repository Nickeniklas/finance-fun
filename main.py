import os

from fastapi import FastAPI

# Wired up now; used by the data module in step 2.
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

app = FastAPI(title="Finance Fun API")


@app.get("/health")
def health():
    return {"status": "ok"}
