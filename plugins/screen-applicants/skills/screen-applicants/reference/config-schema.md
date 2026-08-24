# config.json

Everything the board shows, other than the candidates themselves.

```json
{
  "title": "Coordinator Screening",
  "role": "Operations Manager",
  "company": "Acme Robotics",
  "eyebrow": "Acme Robotics · Screening board",
  "dek": "One or two sentences under the title.",

  "axes": [
    {"key": "ops",      "label": "Operations"},
    {"key": "writing",  "label": "Writing"},
    {"key": "sector",   "label": "Sector"}
  ],

  "criteria": [
    {"h": "Operations depth", "p": "What this axis measures. HTML allowed."},
    {"h": "Filters applied", "p": "State the filters and where they came from."}
  ],

  "stage": {
    "mark": "Next",
    "title": "What happens after this board",
    "body": "One paragraph. HTML allowed.",
    "meta": "Marks are saved in this browser only."
  },

  "tiers": [
    {"key": "A", "title": "Interview first", "stat_label": "Interview",
     "note": "Shown under the heading."},
    {"key": "B", "title": "Second look", "note": "..."},
    {"key": "D", "title": "Outside the area", "style": "list", "note": "..."}
  ],

  "filters": [
    {"key": "local", "label": "Local only", "match": "Denver|Boulder"},
    {"key": "exp",   "label": "Agency experience", "axis": "ops", "min": 3}
  ],

  "mark_label": "Contacted",
  "watch_label": "Watch",
  "cut_label": "Why not",
  "flag_label": "Decide before contacting",
  "now_column": "Current / most recent",
  "footer": {"left": "24 applications", "right": "Closed 1 June 2026"}
}
```

## Notes

**axes** — `key` must match the keys in each candidate's `scores`. Three fits the
card layout best; four still works.

**tiers** — order here is the order on the page. `style: "list"` renders a
compact set-aside group with no scores or documents button; omit it for full
cards. `stat_label` is the short label used in the header counts.

**filters** — either `match` (a regular expression tested against the
candidate's location) or `axis` plus `min` (keeps candidates scoring at least
`min` on that axis). An "All" button is added automatically.

**stats** — omit and the builder generates counts from the data. Supply an array
of `{"n": ..., "l": ...}` to override.

Fields taking HTML: `dek`, `criteria[].p`, `stage.body`, `tiers[].note`, and each
candidate's `current`, `assessment`, `watch`, `decide_first`. Use `<b>` for
emphasis. Everything else is escaped.

## Candidate fields the builder reads

Required: `name`, `tier`, `scores` (every axis, integer 1 to 5).
Optional: `location`, `current`, `assessment`, `watch`, `tags`
(`[["Label", "good|warn|bad"], ...]`), `decide_first`, `email_address`,
`documents` (from extract.py, pass through unchanged).
