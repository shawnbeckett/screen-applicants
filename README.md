# screen-applicants

A Claude Code plugin that reads a folder of job applications against a job
description and builds a ranked screening board you can browse, sort and filter,
with every candidate's real resume and cover letter readable inside it.

Built to replace the version of this job that involves opening forty PDFs one at
a time.

## Install

New to Claude Code? Open [INSTALL.md](INSTALL.md), copy the prompt, paste it in,
and it will handle the setup and check the prerequisites for you.

Otherwise:

```
/plugin marketplace add shawnbeckett/screen-applicants
/plugin install screen-applicants@beckett-tools
```

Then ask for what you want in your own words:

> Screen the applications in ~/Desktop/applications against this job
> description: [paste the posting]

## What it does

1. **Asks first.** Where the applications are, where the posting is, and
   anything the posting does not say that should change the ranking.
2. **Briefs you before it starts.** How it read the role, which requirements it
   treats as absolute, the criteria it proposes to score on, and how it will
   rank. You can drop a criterion, add your own, or change what one means.
3. **Extracts.** Opens `.eml` files, converts PDFs, DOCX and images, works out
   which files are applications and which are unrelated, and groups them into
   candidates by the email address inside each document.
4. **Shows you the roster** and flags anyone it could not confidently identify,
   before scoring.
5. **Scores everyone in one pass**, so a 4 means the same thing at the top and
   bottom of the list.
6. **Publishes a private board.** Ranked groups, a sortable table, filters, and
   a document panel that opens each candidate's actual files.

## Requirements

- Claude Code
- `pdftotext`, for reading PDFs: `brew install poppler`
- `tesseract`, only if applicants send resumes as photographs:
  `brew install tesseract`

DOCX needs nothing extra on macOS.

`reference/setup.md` inside the skill walks through all of this for someone who
has not used Claude Code before.

## How it handles a messy folder

Point it at a junk drawer. In testing against a folder containing scattered
applications plus a utility bill, a government form, six CSVs, a spreadsheet and
a GIF, it put zero unrelated files into any candidate and flagged the people it
could not identify rather than guessing.

Grouping joins on the email address found inside each document rather than the
filename, because filenames are unreliable and nearly every resume carries an
email. Where that fails it says so instead of pairing silently.

## What it does not do

**It reads folders, not inboxes.** Attachments cannot be fetched out of email,
so save them to a folder first and point at that.

**It does not verify anything.** Every number and title on a resume is the
applicant's own claim, and the board quotes them as claims.

**The scores are a judgment, not a measurement.** They are consistent within one
run and not comparable across runs or against another reviewer. Use them as a
reading order, then read the documents.

**It will not score or filter on protected characteristics** or proxies for
them, including name origin, photographs, pronouns, age, gender, ethnicity,
religion, family status or disability. Location and work authorization count
only when the posting states them.

## Licence

MIT
