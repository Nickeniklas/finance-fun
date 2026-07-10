# Events Feed — Daily Routine

You are updating the Events Feed for finance-fun. You maintain two files:
`static/events.json` (deal records) and `static/digest.json` (daily delta +
themes). Your job: scan today's news, judge what's material, merge it into
the existing state, and write both files back.

Today's date: use the actual current date throughout.

## 1. Orient (do this before any searching)

Read, in order:
- `docs/EVENTS_FEATURE.md` — the schema contract. It wins over this prompt
  if they ever disagree.
- `static/events.json` — the full current state. This is your dedup
  reference. Internalize what deals already exist before scanning.
- `static/digest.json` — yesterday's delta and themes. The `themes` array
  is your memory across runs; you will carry, increment, or drop these.
  If the file doesn't exist yet, treat themes as empty and note it.

## 2. Scan

Web search for material company investment events from roughly the last
48 hours. You are looking for:
- M&A (announced, rumored-by-credible-press, approved, closed, blocked,
  abandoned — a bid withdrawn, talks that collapsed, or an offer that
  lapsed)
- Major partnerships and joint ventures
- Capital allocation shifts (major buybacks, dividend policy changes,
  large capex commitments, spin-offs)
- Strategy shifts (market exits/entries, major restructuring)

Scope: global large/mid caps, general market. Give mild extra attention
to Nordic/European names, but do not filter to them.

Use several searches with different angles (e.g. "merger announcement",
"acquisition confirmed", "partnership deal", plus follow-ups on anything
already in events.json that might have advanced). For any deal already in
events.json that hasn't had a phase in 5+ days, do one targeted search to
check whether it advanced.

## 3. Judge materiality

Keep only events where a reasonable investor would say "this could change
the investment case for this company." Concrete rejects:
- Analyst ratings, price-target changes, "top 5 stocks" content
- Routine earnings coverage (unless earnings *contained* a strategic
  announcement — then the announcement is the event, not the earnings)
- Vague executive statements with no committed action
- Rumors from non-credible sources (keep rumors only when reported by
  major financial press)
- Anything where you cannot name the counterparty or the concrete action

When unsure, reject. A short feed of real events beats a long feed with
filler. Zero new events on a quiet day is a valid outcome.

## 4. Match against existing state

For each kept event, decide: new deal, or new phase of an existing deal?

- Deal identity = ticker + counterparty + type, judged semantically (name
  variations, subsidiary names, and ticker vs company name all count as
  the same party). The `id` slug encodes this and never changes once
  created.
- Phase identity = the specific development. Before appending a phase,
  check whether any existing phase of that deal already records the same
  development (same status + substantially same substance, even if the
  headline wording differs). If yes, skip it entirely.

The two failure directions, both of which you must avoid:
- **Duplicate deal**: today's headline is a re-report or advancement of a
  deal already in the file, but you create a second record. Always check
  existing deals for the same parties before creating anything.
- **Wrong merge**: two genuinely different deals between the same parties
  (e.g. a partnership AND a separate acquisition rumor) squeezed into one
  record. Different `type` = different deal, always.

## 5. Update events.json

- New deal → new record matching the schema exactly. Write a sharp
  one-line `whyItMatters` — the investor-relevant "so what", not a
  headline restatement.
- New phase → append to that deal's `phases`, update `currentStatus` to
  the new phase's status. `priceReaction` is whatever the reporting says,
  as a string ("+10% premarket"); if reporting mentions no price move,
  omit the field rather than inventing one. A deal the parties themselves
  dropped (bid withdrawn, talks collapsed, offer lapsed) gets a phase
  ADVANCED to `"abandoned"` — never silently drop it from the file. Use
  `"blocked"` instead when the stop was externally imposed (e.g. a
  regulator).
- **Never edit, reword, or delete existing phases or existing
  whyItMatters text. History is append-only.** The only permitted
  mutations are: append phase, update currentStatus, add new deal,
  remove stale deal.
- Stale: remove any deal whose most recent phase is older than 21 days.
  Count removals for the digest.

## 6. Write digest.json

Regenerate the whole file (it is a snapshot, not a log):

- `date`: today.
- `whatChanged`: one entry per actual change from step 5 — "NEW: …",
  "ADVANCED: … (rumored → confirmed)", "DROPPED: N stale deals". If
  nothing changed, write exactly one entry: "No material changes today."
  Never pad this list.
- `themes`: max 5, ideally 2–4. A theme is a pattern connecting 2+
  *currently active* deals (e.g. "3 deals this month involve chip export
  workarounds"). For each theme in yesterday's digest, decide: still
  supported by active deals → carry it, increment `streak`; no longer
  supported → drop it silently. New theme only when the connection is
  concrete enough that you could name the specific deals behind it —
  and do name them in the `note`. If no honest themes exist, an empty
  array is correct. Do not manufacture connections.

## 7. Validate and commit

- Parse both files as JSON (actually run a parse, e.g. python -c or jq —
  don't eyeball it).
- Sanity checks: every deal has ≥1 phase; every `currentStatus` equals
  its last phase's status; no two deals share an `id`; all dates are
  YYYY-MM-DD.
- Commit both files to main with message
  "events: daily update YYYY-MM-DD (+N new, +M phases, -K stale)".
- Finish with a 3-line summary of what you did.