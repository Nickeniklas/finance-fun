# Events Feed — Schema Contract

Authoritative schema for `static/events.json` and `static/digest.json`. This
file is the source of truth for the daily routine at `routines/events-feed.md`
— **this document wins over that prompt** wherever they disagree. It was
locked from the schema as it actually exists in the two JSON files, not from
what the routine prompt describes.

Do not add a field, status value, or file shape here that isn't already
present in the JSON files unless you are deliberately extending the schema
(see "Extending this schema" at the end).

## `static/events.json`

### Top-level shape

```
{
  "generatedAt": string,   // ISO 8601 datetime, e.g. "2026-07-08T08:00:00Z"
  "events": Deal[]
}
```

- `generatedAt` — required. Full ISO 8601 datetime (not just a date) of the
  last write. Distinct from the `YYYY-MM-DD` date format used everywhere
  else in this schema.
- `events` — required. Array of Deal records, order not meaningful.

### Deal record shape

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Kebab-case slug encoding deal identity (ticker + counterparty + type). Immutable once created — never renamed, even if the deal's details evolve. |
| `ticker` | string | yes | Uppercase primary-company ticker. |
| `counterparty` | string \| null | yes (field always present) | The other party's ticker or company name (mixed forms observed: `"AAPL"`, `"Anthropic"`, `"Sky (Comcast)"`, `"Castlelake"`). `null` when the deal has no counterparty (e.g. a buyback). |
| `type` | string | yes | Observed values: `"partnership"`, `"capital-allocation"`, `"acquisition"`. Not a closed list — new deal types may appear as new kinds of events are tracked. A different `type` between the same two parties always means a different deal (never merge). |
| `currentStatus` | string | yes | **Closed list** — see below. Must always equal the `status` of the last (most recent) entry in `phases`. |
| `whyItMatters` | string | yes | One-line investor-relevant "so what". Written at deal creation; unlike `phases`, it is **not** append-only — a later run may rewrite it if the deal's significance changes materially enough to warrant an updated summary. |
| `phases` | array | yes, ≥1 entry | Strictly append-only. See "Phases array rule" below. |

#### Allowed `status` values (closed list — no others permitted)

- `"rumored"`
- `"confirmed"`
- `"approved"`
- `"closed"`
- `"blocked"`
- `"abandoned"`

This applies to both `currentStatus` and every `phases[].status`. These six
values cover the full deal lifecycle a phase can be in. Only `"rumored"` and
`"confirmed"` appear in the current data, but the other four are legitimate
and expected as tracked deals progress (e.g. a take-private moving from
`"confirmed"` to regulatory `"approved"` to `"closed"`, or a bid that gets
`"blocked"`). Do not invent a seventh value without first updating this
document (see "Extending this schema").

`"blocked"` and `"abandoned"` are both terminal, but distinct in cause:
`"blocked"` is an externally imposed stop (e.g. a regulator rejects the
deal); `"abandoned"` is a voluntary withdrawal by the parties themselves
(bid withdrawn, talks collapsed, offer lapsed) with no external party
forcing the outcome.

#### Phase object shape

| Field | Type | Required | Notes |
|---|---|---|---|
| `status` | string | yes | One of the closed list above. |
| `date` | string | yes | `YYYY-MM-DD`. |
| `headline` | string | yes | The reported headline, not a paraphrase. |
| `source` | string | yes | Publisher name, e.g. `"Reuters"`, `"CNBC"`. |
| `priceReaction` | string | no | Free-text like `"+10% premarket"`. **Omit the field entirely** when the reporting mentions no price move — never invent one. |

#### Phases array rule (append-only)

- `phases` only ever grows. A run may **append** a new phase object to the
  end of the array; it must never edit, reorder, or delete an existing
  phase entry, regardless of new information.
- Before appending, check whether an existing phase already records the
  same development (same `status` + substantially the same substance, even
  if headline wording differs elsewhere). If so, skip — do not append a
  duplicate.
- When a phase is appended, `currentStatus` is updated to match that new
  phase's `status`.
- The only permitted mutations to an existing deal record are: append a
  phase, update `currentStatus` to match the newly-appended phase, and
  (optionally) rewrite `whyItMatters` if the deal's significance changed
  enough to warrant it. `ticker`, `counterparty`, `type`, and any prior
  phase entry must never change.
- Removing a whole deal record (stale-deal cleanup, 21+ days since its most
  recent phase) is the one allowed deletion, and it removes the entire
  record, never a partial edit within it.

## `static/digest.json`

Regenerated from scratch on every run — a snapshot of the latest run, not an
append-only log like `events.json`.

### Top-level shape

```
{
  "date": string,          // YYYY-MM-DD
  "whatChanged": string[],
  "themes": Theme[]
}
```

- `date` — required, `YYYY-MM-DD` (date only — unlike `events.json`'s
  `generatedAt`, no time component).
- `whatChanged` — required array of strings, one entry per actual change
  made to `events.json` in this run:
  - `"NEW: <description>"` — a new deal record was created.
  - `"ADVANCED: <description> (<oldStatus> → <newStatus>)"` — a phase was
    appended to an existing deal.
  - `"DROPPED: N stale deals"` — N deals removed for being 21+ days stale.
  - If literally nothing changed, the array must contain **exactly one**
    entry, the literal string `"No material changes today."`, and no other
    entries. Never combine it with other entries, and never pad the array
    with non-changes.
- `themes` — required array, 0–5 entries (target 2–4). Empty array is a
  valid, honest outcome when no theme is currently supported.

### Theme object shape

| Field | Type | Required | Notes |
|---|---|---|---|
| `label` | string | yes | Short name for the pattern, e.g. `"UK-listed franchises broken up or taken private"`. |
| `note` | string | yes | Explanation of the pattern. **Must name the specific deal `id`(s)** from `events.json` that support it (parenthetical references like `(ezj-castlelake-takeover)`), not just company names — a note that only gestures at "a couple of deals" without citable ids is invalid. |
| `streak` | integer | yes | Number of consecutive daily runs this theme has been carried. |

#### Streak counter rule

- A brand-new theme starts at `streak: 1`.
- On each subsequent run: if the theme is still supported by ≥2 *currently
  active* deals in `events.json`, carry it forward and increment `streak`
  by 1.
- If a theme from yesterday's digest is no longer supported (fewer than 2
  active deals back it, e.g. because a supporting deal went stale and was
  removed), **drop it silently** — do not carry it at `streak: 0` or note
  the drop in the theme list itself (the drop itself may be worth a
  `whatChanged` line if desired, but is not required by this schema).
- Never manufacture a theme just to keep a streak alive — the connection
  must be concrete enough to name the deals behind it.

## Validation checks (must pass before writing either file)

A run must not write `events.json` or `digest.json` unless all of the
following hold:

1. Both files parse as valid JSON (actually parse them — e.g. `python -c
   "import json; json.load(open(...))"` or `jq .` — do not eyeball it).
2. Every deal in `events.json` has `phases.length >= 1`.
3. Every deal's `currentStatus` exactly equals the `status` of the last
   entry in its `phases` array.
4. No two deals share the same `id`.
5. Every date value (`events.json` phase `date`, `digest.json` `date`) matches
   `YYYY-MM-DD`; `events.json`'s top-level `generatedAt` matches full ISO
   8601 datetime.
6. Every `status` value (both `currentStatus` and all `phases[].status`) is
   one of the closed list: `"rumored"`, `"confirmed"`, `"approved"`,
   `"closed"`, `"blocked"`, `"abandoned"`.
7. Compared to the previous `events.json`, no existing deal's `phases` array
   had an entry edited, reordered, or removed (only appends, or
   whole-record removal for staleness, are legal diffs). `whyItMatters` may
   legitimately differ from the previous run.
8. Any deal whose most recent phase is 21+ days old has been removed, and
   that removal is counted in `digest.json`'s `whatChanged`.
9. `digest.json`'s `whatChanged` is either exactly `["No material changes
   today."]` or contains only substantive `NEW:` / `ADVANCED:` / `DROPPED:`
   entries (never both).
10. `digest.json`'s `themes` array has at most 5 entries.
11. Every theme's `note` names at least one deal `id` that actually exists
    in the current `events.json`.

## Extending this schema

If a run needs a `status` value outside the closed list, a new `type`
category, or any new field, update this document first (in a separate
change, reviewed on its own), then have the routine write data conforming
to the updated contract. Never let written data silently drift ahead of
what's documented here.
