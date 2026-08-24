# Setup, for a first-time Claude Code user

## What you need once

**Claude Code.** Install from claude.com/claude-code, then sign in with the
Claude account you already use.

**One command-line tool.** The extractor reads text out of PDFs using a program
called `pdftotext`. Open Terminal and paste:

```bash
brew install poppler
```

If `brew` is not found, install Homebrew first from brew.sh, then run the line
above.

Optional, only needed if any applicant sends a resume as a photograph or a
screenshot rather than a document:

```bash
brew install tesseract
```

DOCX files need nothing extra on a Mac.

**The skill.** It lives in `~/.claude/skills/screen-applicants/`. If someone
sent you the folder, put it there, keeping the folder name.

Check it worked by opening Terminal and running:

```bash
python3 ~/.claude/skills/screen-applicants/scripts/extract.py
```

You should see usage instructions rather than an error about the file not
existing.

## Each time you screen a role

1. Put every application in one folder. It does not need tidying. Forwarded
   emails saved as `.eml`, loose PDFs, Word files, a stray screenshot: all fine.
   Unrelated files in the same folder are set aside rather than mixed in.

   If they arrived by email, save the attachments into a folder first. Claude
   cannot pull them out of your inbox, so this step is yours. In Gmail that is
   **Download all attachments** at the top of the attachment strip, which gives
   you a zip to unzip.

2. Open Terminal, type `claude`, press Return.

3. Tell it what you want, in your own words. For example:

   > Screen the applications in ~/Desktop/PR-Coordinator-Applications against
   > this job description: [paste the posting]

4. It will ask a few questions first: where the applications are, where the job
   description is, and whether there is anything else it should know that the
   posting does not say. Answer the last one honestly. A start date, a budget
   that moved, or someone you already know changes the ranking.

5. Then it stops and tells you what it is about to do: how many applications it
   found, how it read your posting, which requirements it treats as absolute,
   the criteria it proposes to score on, and how it will rank. Read this part
   properly. You can drop any criterion, add your own, or change what one
   means. Everything downstream depends on it.

6. It will show you the candidates it found and flag anyone it could not
   confidently identify. Correct anything wrong before it starts scoring.

7. You get a link to a private board: everyone ranked, with their real resume
   and cover letter readable inside it.

## Things worth knowing

**The board is private.** Nobody sees it unless you use the Share button.

**The scores are a judgment, not a measurement.** They are consistent within one
run because one pass produces all of them. They are not comparable to a
different run or to another person's opinion. Treat them as a reading order,
then read the documents.

**Everything on a resume is a claim.** The board quotes applicants' own numbers
and titles. None of it is verified.

**Check the grouping.** Files are matched to people mostly by the email address
inside them. It is usually right and occasionally not, which is why it asks you
to confirm before scoring.

## If something goes wrong

*"pdftotext: command not found"* — run `brew install poppler`.

*A candidate is named "Unidentified"* — their documents had no email address and
no readable name. Tell Claude who it is.

*Two people merged into one, or one person split in two* — say so, and Claude
will correct the grouping and rebuild.

*Someone's resume looks scrambled* — that resume is probably an image or an
unusual layout. Tell Claude which candidate and it will re-extract that file.
