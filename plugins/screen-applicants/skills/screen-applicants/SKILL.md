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

### 1. Locate the two inputs

**Treat every run as the first one.** Ask plainly, in plain text, and offer no
options. Do not use AskUserQuestion here: a path is free text, and a picker
forces you to invent choices you will fill from whatever is lying around in the
conversation. Never suggest a folder, a file or a role mentioned earlier in this
session or in a previous run. The operator's machine is not the one you were
last working on.

Ask for these two, in this order, and wait for each:

**1. The job description.** A file path, or paste the posting. Ask for it first
and do not continue without it. Never infer the role from the resumes: that
reverse-engineers the posting from whoever happened to apply.

**2. The applications folder.** A folder path. This is the only supported input.
If they are still in an inbox, say plainly that you cannot fetch attachments out
of email and that they need saving to a folder first. In Gmail that is
**Download all attachments** on the message, which gives a zip to unzip. Never
offer to read them from email directly.

If a path does not exist, say so and ask again. Do not guess a nearby one.

### 2. Read the job description properly

Do this before looking at a single application, and before proposing anything.
Read the whole posting and work out:

- **What the role actually is.** Day-to-day work, seniority, who it reports to,
  what a good week looks like.
- **Required against preferred.** Postings mix the two in one list. Separate
  them. A stated requirement becomes a hard filter; a preference becomes a
  scored axis.
- **The constraints.** Location, time zone, authorization, salary band, start
  date, sectors, travel.
- **What the employer is optimising for.** Often unstated and visible in
  emphasis, repetition and what the posting spends its words on. A junior
  posting stressing mentorship wants coachability. One listing named tools wants
  someone productive immediately.
- **What would make a strong candidate wrong for this.** Usually seniority above
  the band, or a sector that does not transfer.

Count the applications in the folder while you are here, so the brief can say
how many.

### 3. Ask what the posting does not say

Now that you understand the role, ask one open question, and make it specific to
what you just read rather than generic. Name the gaps you noticed: no start
date, no team size, a band that looks low for the experience being asked for.

Take whatever comes back, including nothing. Constraints, preferences, a
candidate already known to them, someone to exclude, a budget that moved. Also
ask how many they want in the top group, if they have a view.

### 4. Brief the operator, then stop

State the plan and **wait**. Five parts, in this order:

1. **What I am about to do.** "Screening 38 applications from
   ~/Desktop/applications against the PR Account Coordinator posting."
2. **How I read the posting.** Three or four sentences from step 2 on what this
   role is and what the employer is optimising for. This is where a misreading
   becomes visible, so make it specific enough to be wrong.
3. **Stated requirements.** What the posting demands as opposed to prefers,
   quoted or closely paraphrased, plus anything they added in step 3.
4. **Proposed scoring axes.** Three or four, each with a one-line definition and
   a note on what a 1 and a 5 look like. Derived from this posting, never reused
   from another role.
5. **How ranking will work.** Which axes carry weight, which requirements are
   hard filters that set a candidate aside rather than lower their score, and
   what the output groups will be called.

### 5. Let them change the criteria

Do not just ask "does this look right". Offer the edit explicitly:

- Drop any proposed axis
- Add one of their own, and score it like the others
- Change what an axis means
- Move a requirement between hard filter and scored axis
- Rename the output groups

Then restate the final criteria in one short block and get a clear yes. Getting
this wrong wastes the entire run.

### 6. Extract

```bash
python3 scripts/extract.py <applications-folder> <work-folder>
```

Walks the folder, opens `.eml` files, converts every PDF, DOCX and image,
decides which files are applications, and groups them into candidates by email
address. Writes `candidates.json` and `report.json`.

### 7. Confirm the roster

Show the operator: how many candidates were found, anyone named
"Unidentified", anything in `report.json` under `review_these`, and what was set
aside. **Grouping is a guess.** Fix any errors before scoring, because a
mis-paired document silently corrupts a candidate's assessment.

### 8. Read and score

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

### 9. Build and publish

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
| Offering folder or JD options drawn from earlier in the session | Those paths do not exist for this operator; ask, do not suggest |
| Using a picker for file paths | A path is free text; a picker makes you invent choices |
| Extracting before the operator approved the criteria | The run is wasted if the axes were wrong |
| Asking "does this look right" instead of offering edits | Operators accept a default they would have changed |
| Offering to read applications straight out of email | Attachments cannot be fetched; they must be saved to a folder first |
| Scoring candidates in separate agents | Scales drift; one agent's 4 is another's 3 |
| Reusing a previous role's axes | Axes must come from this posting |
| Proposing axes before reading the whole posting | The axes are the run; skimming produces generic ones |
| Inferring the role from the resumes | That reverse-engineers the job from whoever applied |
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
