# Install

You do not need to understand any of this. Copy the block below, paste it into
Claude Code, and it will do the setup and tell you the one or two things only
you can do.

## Step 1

Open Terminal. Type `claude` and press Return.

## Step 2

Copy everything between the lines below and paste it in.

---

```
Please install the screen-applicants plugin for me. I have not used Claude Code
much, so explain what you are doing in plain language and ask before anything
that changes my machine.

Do these in order:

1. Check whether pdftotext is installed by running: which pdftotext
   If it is missing, tell me you need to install a package called poppler that
   lets you read PDFs, and ask permission. If I agree, check whether Homebrew is
   present with: which brew
   If Homebrew is missing, do not try to install it silently. Give me the one
   line to paste from brew.sh and wait for me to say it is done.
   Once Homebrew is available, run: brew install poppler

2. Ask whether any applicant is likely to send a resume as a photograph or a
   screenshot rather than a document. If yes, offer to also run:
   brew install tesseract
   If no, skip it. It is not needed otherwise.

3. Tell me to type these two lines, one at a time, and wait for me to confirm.
   You cannot type them yourself because they are commands only I can run:

       /plugin marketplace add shawnbeckett/screen-applicants
       /plugin install screen-applicants@beckett-tools

4. Once I confirm, verify the install by checking that this file exists:
   ~/.claude/plugins/cache/beckett-tools/screen-applicants/*/skills/screen-applicants/SKILL.md
   If the path differs on my machine, search under ~/.claude/plugins for
   SKILL.md instead of guessing. Tell me plainly whether it worked.

5. If the plugin commands fail for any reason, fall back to a direct install
   instead, and tell me you are doing that:
       git clone https://github.com/shawnbeckett/screen-applicants.git /tmp/sa-install
       mkdir -p ~/.claude/skills
       cp -R /tmp/sa-install/plugins/screen-applicants/skills/screen-applicants ~/.claude/skills/
       rm -rf /tmp/sa-install
   This works the same way but I will have to repeat it to get updates.

6. When it is installed, show me one short example of how to actually use it,
   using a folder path on my own machine, and stop. Do not run a screening
   unless I ask.
```

---

## Step 3

When it says the install worked, restart Claude Code so it picks up the new
skill. Quit the Terminal window and open a new one, then type `claude` again.

## Using it

Put every application in one folder. It does not need tidying: forwarded emails
saved as `.eml`, loose PDFs, Word files, a stray screenshot are all fine, and
unrelated files in the folder are set aside rather than mixed in.

If the applications arrived by email, save the attachments to a folder first.
Claude cannot pull them out of your inbox. In Gmail that is **Download all
attachments** at the top of the attachment strip, which gives you a zip to
unzip.

Then ask for what you want:

> Screen the applications in ~/Desktop/applications against this job
> description: [paste the posting]

It will ask you a few questions, then stop and tell you how it read the posting
and what it plans to score on before it does any work. That is the part worth
reading. You can change any of it.

## Updating later

```
/plugin update screen-applicants@beckett-tools
```

## If you get stuck

Paste the error into Claude Code and ask what it means. It has the setup guide
at `reference/setup.md` inside the skill and can read it.
