import os

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

app = FastAPI(title="Finance Fun API")


@app.get("/health")
def health():
    return {"status": "ok"}
