# Prompt Library — Contract

A curated, **standalone**, read-only collection of finance/stock prompts. It does
**not** touch the data layer in v1. The user picks a prompt; it drops into a text
field (or clipboard) with placeholders intact; the user fills in the ticker etc.
themselves wherever they paste it (their own ChatGPT/Claude).

This decoupling is deliberate: lowest complexity, no dependency on Finnhub, no
"which data fields does this prompt need" logic. Auto-filling prompts with live
fetched data is a clean **v2** enhancement (same library + a data-pouring step).

---

## Storage

A static JSON file in the repo. Read-only, authored by the owner. No database.
The number of prompts is irrelevant to the architecture — works with 3 or 30.

## Record shape

```jsonc
{
  "id": "compare-valuation",
  "title": "Compare two stocks on valuation",
  "category": "comparison",          // e.g. valuation | comparison | news-analysis
  "description": "Side-by-side valuation read on two tickers.",
  "text": "Compare [TICKER 1] and [TICKER 2] on valuation. Look at P/E, P/B, and EV/EBITDA, and tell me which looks cheaper relative to its growth."
}
```

Placeholders are **human-readable** and left for the user: `[TICKER]`,
`[TICKER 1] vs [TICKER 2]`, etc. No machine substitution in v1.

## Frontend behavior (v1)

- List prompts, grouped or filterable by `category`.
- Each prompt shows `title` + `description`.
- "Copy" / "Try this" puts `text` (placeholders intact) into a text field or the
  clipboard for the user to paste elsewhere.

## v2 hook

The same records become LLM inputs: feed `text` (optionally with live data poured
into placeholders) to a call made with the **user's own API key**, held in the
browser only and never stored server-side. Nothing in the v1 shape blocks this.

---

## Content note

Writing the actual prompts is a content task, separable from the build. Start with a
few and grow. The structure above does not change as the library grows.
