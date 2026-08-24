---
name: screen-applicants
description: Use when someone has a folder of job applications and a job description and needs them read, compared and shortlisted. Triggers include screening candidates, reviewing resumes, ranking applicants, building a shortlist, sorting a pile of CVs, or deciding who to interview.
---

# Screen applicants

Turns a folder of applications plus a job description into a ranked, browsable
screening board published as an artifact. Every candidate's real resume and
cover letter stays readable inside the board, so any ranking can be checked
against the source.

**Core principle: one reader scores everyone.** Scores are only comparable when a
single pass assigns all of them against one calibration. Never split scoring
across parallel agents.

## Workflow

### 1. Intake

Ask before assuming. Use AskUserQuestion so the operator picks rather than
types. Establish four things:

**Where the applications are.** A folder path. If they are sitting in an inbox,
say this plainly: Gmail cannot hand over attachments through the API, so they
must be downloaded first. In Gmail, open the message and use **Download all
attachments**, which produces a zip. Unzip it and point at that folder. Do not
promise to read them out of email directly.

**Where the job description is.** A file path, or pasted text. Ask for it if it
was not supplied. Never infer the role from the resumes.

**Anything else worth knowing.** One open question: constraints, preferences, or
context the posting does not carry. Start date pressure, a candidate already
known to them, a budget that moved, someone to exclude. Offer it as free text
and take whatever comes back, including nothing.

**How many they want in the top group**, if they have a view. Otherwise decide
from the field and say so.

### 2. Look, then brief the operator before doing anything

Count the files and read the posting. Then state the plan and **stop**. The
brief has five parts, in this order:

1. **What I am about to do.** "Screening 38 applications from
   ~/Desktop/applications against the PR Account Coordinator posting."
2. **How I read the posting.** Three or four sentences on what this role
   actually is and what the employer seems to be optimising for. This is where a
   misreading becomes visible, so make it specific enough to be wrong.
3. **Stated requirements.** What the posting demands as opposed to prefers,
   quoted or closely paraphrased: experience floor, location, time zone,
   authorization, salary band, sectors.
4. **Proposed scoring axes.** Three or four, each with a one-line definition and
   a note on what a 1 and a 5 look like. Derived from this posting, never reused
   from another role.
5. **How ranking will work.** Which axes carry weight, which requirements are
   hard filters that set a candidate aside rather than lower their score, and
   what the output groups will be called.

### 3. Let them change the criteria

Do not just ask "does this look right". Offer the edit explicitly:

- Drop any proposed axis
- Add one of their own, and score it like the others
- Change what an axis means
- Move a requirement between hard filter and scored axis
- Rename the output groups

Then restate the final criteria in one short block and get a clear yes. Getting
this wrong wastes the entire run.

### 4. Extract

```bash
python3 scripts/extract.py <applications-folder> <work-folder>
```

Walks the folder, opens `.eml` files, converts every PDF, DOCX and image,
decides which files are applications, and groups them into candidates by email
address. Writes `candidates.json` and `report.json`.

### 5. Confirm the roster

Show the operator: how many candidates were found, anyone named
"Unidentified", anything in `report.json` under `review_these`, and what was set
aside. **Grouping is a guess.** Fix any errors before scoring, because a
mis-paired document silently corrupts a candidate's assessment.

### 6. Read and score

Under 25 candidates: read them directly.

25 or more: dispatch one subagent per candidate to return a **factual digest
only** (roles, years, sectors, tools, education, location, stated
authorization, notable claims) using a fixed schema. No scores, no ranking.
Keeps document text out of the main context.

Then score every candidate **in one pass** over the digests. See
`reference/scoring.md` for the rubric and the assessment style.

Write the scored file: start from `candidates.json` and add `tier`, `scores`,
`location`, `current`, `assessment`, `watch`, optional `tags` and
`decide_first`. Keep the `documents` array untouched.

### 7. Build and publish

```bash
python3 scripts/build.py <scored.json> <config.json> <output.html>
```

Refuses to build if any candidate is missing a tier or an axis score. Then
publish `output.html` as an artifact and give the operator the link.

## Quick reference

| File | Purpose |
|---|---|
| `scripts/extract.py` | folder to grouped candidates with text |
| `scripts/build.py` | scored JSON to publishable board |
| `assets/template.html` | the board itself, driven by config |
| `reference/config-schema.md` | every config field, with an example |
| `reference/scoring.md` | how to derive axes and write assessments |
| `reference/setup.md` | first-time setup, for a new Claude Code user |

## Common mistakes

| Mistake | Why it breaks |
|---|---|
| Extracting before the operator approved the criteria | The run is wasted if the axes were wrong |
| Asking "does this look right" instead of offering edits | Operators accept a default they would have changed |
| Offering to read applications straight out of Gmail | The API cannot fetch attachments; they must be downloaded |
| Scoring candidates in separate agents | Scales drift; one agent's 4 is another's 3 |
| Reusing a previous role's axes | Axes must come from this posting |
| Skipping roster confirmation | A mis-paired resume corrupts an assessment silently |
| Filtering on anything the posting does not state | Screening on unstated criteria invites a discrimination claim |
| Treating resume claims as verified | Every number on a resume is the applicant's assertion |
| Building before every candidate is scored | `build.py` will refuse, by design |

## Guardrails

Do not score, rank, filter or sort on protected characteristics, or on proxies
for them: name origin, photograph, pronouns, age, gender, ethnicity, religion,
marital or family status, disability. If asked to, decline and say why once.
Location and work authorization are legitimate only when the posting states
them.
