# finance-fun

A public (no-login) finance site. Compare stocks, read finance news, track favorite
tickers with a price chart, and browse a curated prompt library.

See [`docs/PLAN.md`](docs/PLAN.md) for the full project plan and rationale.

---

## Current status

**Step 1 complete** — FastAPI skeleton is live with a `/health` endpoint and is
deployable to Render. No data calls yet.

**Next: Step 2** — data module + `/quote/{symbol}` end to end with Finnhub cache.

### Build order

- [x] Step 1 — FastAPI skeleton, Render deploy pipeline
- [ ] Step 2 — Data module + `/quote/{symbol}` (Finnhub, cache)
- [ ] Step 3 — Remaining endpoints: candles, fundamentals, news
- [ ] Step 4 — Frontend shell, watchlist (localStorage), one chart
- [ ] Step 5 — Compare view, news view
- [ ] Step 6 — Prompt library (static JSON + copy UI)

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Vanilla HTML / CSS / JS |
| Charts | TradingView Lightweight Charts |
| Backend | Python + FastAPI |
| Hosting | Render (free tier) |
| Data | Finnhub free tier (60 calls/min) |
| Favorites | Browser localStorage |
| Prompt library | Static JSON in repo |

---

## Local development

```powershell
# First time only
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt

# Start the dev server
.\.venv\Scripts\uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/health` — should return `{"status":"ok"}`.

**VS Code:** select `.venv/Scripts/python.exe` as the Python interpreter
(`Ctrl+Shift+P → Python: Select Interpreter`).

---

## Render deployment

1. Push to GitHub.
2. In [Render](https://render.com) → **New → Web Service** → connect your repo.
3. Set these in the Render dashboard:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment** → add `FINNHUB_API_KEY` with your key.
5. Deploy — Render assigns a public URL automatically.

**Never commit the API key** — it must live only in Render's environment variables.

> Free-tier services spin down after ~15 min of inactivity and take ~1 min to wake on
> the next request. This is fine for a low-traffic hobby site.

---

## Docs

| File | Contents |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | Full project plan, stack rationale, architecture |
| [`docs/DATA_MODULE.md`](docs/DATA_MODULE.md) | Data module contract: endpoints, cache TTLs, output shapes |
| [`docs/PROMPT_LIBRARY.md`](docs/PROMPT_LIBRARY.md) | Prompt library contract: record shape, frontend behaviour |
| [`CLAUDE.md`](CLAUDE.md) | Operating brief for Claude Code |
