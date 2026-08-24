#!/usr/bin/env python3
"""
Turn a messy folder into a clean per-candidate application set.

    python3 extract.py <input-folder> <output-folder>

Walks the folder recursively. Opens .eml files and pulls out their bodies and
attachments. Converts every PDF, DOCX and image it finds to text. Decides which
of those are job-application documents and which are unrelated. Groups the
application documents into candidates, joining on email address first and
person name second.

Writes:
    <output>/candidates.json   grouped candidates with full document text
    <output>/report.json       what was skipped, what was uncertain

Nothing is deleted and nothing is silently dropped. Every input file appears in
either candidates.json or report.json.
"""
import sys, os, re, json, subprocess, email, shutil, tempfile, unicodedata
from email import policy

DOC_EXT = {".pdf", ".docx", ".doc", ".rtf", ".txt", ".md",
           ".jpg", ".jpeg", ".png", ".webp", ".heic"}
SKIP_EXT = {".zip", ".mp4", ".mov", ".mp3", ".wav", ".xlsx", ".csv",
            ".pptx", ".key", ".numbers", ".pages", ".ics", ".vcf"}
BULLETS = "•●▪◦‣∙"

EMAIL_RE = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
PHONE_RE = re.compile(r'(\+?\d[\d\s().-]{7,}\d)')


# ---------------------------------------------------------------- text cleanup
def norm(s):
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("​", "").replace("﻿", "").replace("\xa0", " ")
    s = re.sub(r"[‘’]", "'", s)
    s = re.sub(r'[“”]', '"', s)
    return s


def split_columns(text):
    """Detect a persistent vertical gutter and read column by column.
    Returns (text, did_split)."""
    pages, out, did = text.split("\f"), [], False
    for page in pages:
        lines = [l.rstrip() for l in page.split("\n")]
        body = [l for l in lines if l.strip()]
        if len(body) < 12:
            out.append(page); continue
        width = max((len(l) for l in body), default=0)
        if width < 60:
            out.append(page); continue
        occ = [0] * width
        for l in body:
            for i, ch in enumerate(l[:width]):
                if ch != " ":
                    occ[i] += 1
        n = len(body)
        blank = {i for i in range(width) if occ[i] <= n * 0.02}
        runs, start = [], None
        for i in range(width):
            if i in blank:
                if start is None:
                    start = i
            elif start is not None:
                runs.append((start, i - 1)); start = None
        if start is not None:
            runs.append((start, width - 1))
        cand = [r for r in runs if r[0] > 18 and r[1] < width - 12 and (r[1] - r[0] + 1) >= 4]
        if not cand:
            out.append(page); continue
        g = max(cand, key=lambda r: r[1] - r[0]); cut = g[1] + 1
        left = [l[:cut].rstrip() for l in lines]
        right = [l[cut:].rstrip() for l in lines]
        ln = len([l for l in left if l.strip()])
        rn = len([l for l in right if l.strip()])
        if ln < max(5, n * 0.20) or rn < max(5, n * 0.20):
            out.append(page); continue
        did = True
        out.append("\n".join(left).strip() + "\n\n" + "\n".join(right).strip())
    return "\f".join(out), did


CONT = re.compile(r'^(and|or|but|with|including|to|for|of|in|on|at|the|a|an|that|'
                  r'which|as|by|from|while|through|across|their|its|his|her)\b', re.I)
DATE_LINE = re.compile(r'^\s*(\d{2}/\d{4}|\d{4})\s*[–—-]\s*'
                       r'(\d{2}/\d{4}|\d{4}|present)\s*$', re.I)
LABEL = re.compile(r'^[A-Z][A-Za-z]{2,14}:')


def _struct(l):
    s = l.strip()
    if not s:
        return True
    if DATE_LINE.match(s) or LABEL.match(s):
        return True
    letters = [c for c in s if c.isalpha()]
    if letters and len(s) <= 44 and sum(1 for c in letters if c.isupper()) / len(letters) > 0.85:
        return True
    return False


def reflow(text):
    """Rejoin PDF hard-wrapped lines into paragraphs without changing any words."""
    lines = [l for l in text.split("\n")
             if not (l.strip() and all(c in BULLETS + " -–—·." for c in l.strip()))]
    out = []
    for raw in lines:
        l = raw.rstrip()
        if not l.strip():
            out.append(""); continue
        if not out or not out[-1].strip():
            out.append(l); continue
        prev, cur = out[-1], l.strip()
        if _struct(prev) or _struct(cur):
            out.append(l); continue
        if prev.endswith("-") and cur[:1].islower():
            out[-1] = prev + cur; continue
        if (cur[:1].islower() or CONT.match(cur)) and not re.search(r'[.!?]["\')\]]?$', prev):
            out[-1] = prev.rstrip() + " " + cur; continue
        out.append(l)
    t = "\n".join(out)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    return re.sub(r'\n{3,}', '\n\n', t).strip()


def words(s):
    return re.findall(r"[0-9A-Za-zÀ-ɏ']+", (s or "").lower())


def penalty(t):
    lines = t.split("\n")
    body = [l for l in lines if l.strip()]
    if not body:
        return 1e9
    orphan = sum(1 for l in body if all(c in BULLETS + " -" for c in l.strip()))
    gaps = sum(1 for l in body if re.search(r'\S {5,}\S', l))
    frag = sum(1 for l in body if 0 < len(l.strip()) < 14)
    blanks = sum(1 for l in lines if not l.strip())
    return (orphan * 8 + gaps * 1.2 + frag * .5 + (blanks / len(lines)) * 20) / len(body) * 100


# ---------------------------------------------------------------- conversion
def have(cmd):
    return shutil.which(cmd) is not None


def to_text(path):
    """Return (text, mode). mode 'mono' keeps alignment, others are reflowed."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            if not have("pdftotext"):
                return "", "missing-pdftotext"
            lay = norm(subprocess.run(["pdftotext", "-layout", path, "-"],
                                      capture_output=True, timeout=90).stdout.decode("utf-8", "replace"))
            flo = norm(subprocess.run(["pdftotext", path, "-"],
                                      capture_output=True, timeout=90).stdout.decode("utf-8", "replace"))
            if lay.strip():
                col, did = split_columns(lay)
                if did and col.strip():
                    return reflow(col), "cols"
            cands = []
            if flo.strip():
                cands.append(("flow", flo))
            if lay.strip():
                cands.append(("mono", lay))
            if not cands:
                return "", "empty"
            p, m, t = sorted(((penalty(t), m, t) for m, t in cands), key=lambda x: x[0])[0]
            return (t if m == "mono" else reflow(t)), m
        if ext in (".docx", ".doc", ".rtf", ".pages"):
            if have("textutil"):
                t = norm(subprocess.run(["textutil", "-convert", "txt", "-stdout", path],
                                        capture_output=True, timeout=90).stdout.decode("utf-8", "replace"))
                return reflow(t), "flow"
            return "", "missing-textutil"
        if ext in (".txt", ".md"):
            return reflow(norm(open(path, errors="replace").read())), "flow"
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
            if not have("tesseract"):
                return "", "missing-tesseract"
            with tempfile.TemporaryDirectory() as td:
                base = os.path.join(td, "o")
                subprocess.run(["tesseract", path, base], capture_output=True, timeout=120)
                p = base + ".txt"
                if os.path.exists(p):
                    return reflow(norm(open(p, errors="replace").read())), "ocr"
            return "", "ocr-failed"
    except Exception as e:
        return "", "error:%s" % type(e).__name__
    return "", "unsupported"


# ---------------------------------------------------------------- classify
RESUME_HINTS = ["work experience", "professional experience", "employment",
                "education", "skills", "certifications", "relevant experience",
                "career summary", "professional summary", "core competencies",
                "work history", "qualifications"]
LETTER_HINTS = ["dear ", "to whom it may concern", "i am writing", "i'm writing",
                "please find attached", "thank you for your time",
                "i would welcome", "sincerely", "kind regards", "warm regards",
                "excited to apply", "interest in the", "application for"]
NEGATIVE = ["invoice", "amount due", "purchase order", "statement of account",
            "whereas", "this agreement", "terms and conditions", "tax receipt",
            "remittance", "packing slip", "shareholder", "minutes of meeting",
            "policy number", "premium due", "account balance"]


def classify(text, filename):
    """Return (kind, is_application, confidence 0-1)."""
    t = (text or "").lower()
    fn = filename.lower()
    if len(t.strip()) < 60:
        return "unreadable", False, 0.0

    neg = sum(1 for k in NEGATIVE if k in t)
    res = sum(1 for k in RESUME_HINTS if k in t)
    let = sum(1 for k in LETTER_HINTS if k in t)
    has_contact = bool(EMAIL_RE.search(t)) or bool(PHONE_RE.search(t))
    dates = len(re.findall(r'\b(19|20)\d{2}\b', t))

    fn_res = any(k in fn for k in ("resume", "cv", "curriculum", "résumé"))
    fn_let = any(k in fn for k in ("cover", "letter", "coverletter"))
    fn_port = "portfolio" in fn
    fn_ref = "reference" in fn or "recommendation" in fn
    fn_sample = any(k in fn for k in ("sample", "pitch", "press release", "writing",
                                      "press kit", "presskit", "case study", "clip"))

    if neg >= 2 and res == 0 and not fn_res:
        return "not-an-application", False, 0.85

    score = 0.0
    if fn_res: score += .45
    if fn_let: score += .45
    if fn_port or fn_ref or fn_sample: score += .45
    if res >= 3: score += .40
    elif res == 2: score += .25
    if let >= 3: score += .35
    elif let == 2: score += .20
    if has_contact: score += .15
    if dates >= 3: score += .10
    score = min(score, 1.0)

    if fn_ref: kind = "Reference letter"
    elif fn_port: kind = "Portfolio"
    elif fn_sample: kind = "Writing sample"
    elif fn_let or (let >= 3 and res < 3): kind = "Cover letter"
    elif fn_res or res >= 2: kind = "Resume"
    elif let >= 2: kind = "Cover letter"
    else: kind = "Document"

    return kind, score >= 0.45, round(score, 2)


# ---------------------------------------------------------------- identity
STOP_TOKENS = {"resume", "cv", "curriculum", "vitae", "cover", "letter", "portfolio",
               "application", "final", "updated", "new", "copy", "draft", "docx", "pdf",
               "work", "works", "sample", "samples", "press", "kit", "case", "study",
               "clip", "clips", "media", "writing", "pitch", "release", "reference",
               "recommendation", "tma", "agency", "micdrop"}
# a line starting with one of these is a salutation or sign-off, never a name
SALUTATION = {"dear", "hi", "hello", "hey", "to", "re", "attn", "attention",
              "sincerely", "best", "regards", "thanks", "thank", "warm", "kind",
              "yours", "greetings", "good", "by", "from", "subject", "date"}
# resume section headings look like two capitalised words but are not people
HEADING_WORDS = {"skill", "skills", "set", "work", "experience", "education",
                 "summary", "profile", "contact", "objective", "references",
                 "reference", "projects", "project", "awards", "award",
                 "languages", "language", "interests", "certifications",
                 "certification", "employment", "history", "background",
                 "achievements", "highlights", "competencies", "qualifications",
                 "volunteer", "activities", "publications", "training",
                 "professional", "personal", "details", "information", "about"}
ROLE_WORDS = ("manager", "coordinator", "specialist", "director", "assistant",
              "intern", "officer", "consultant", "analyst", "associate", "engineer",
              "designer", "developer", "executive", "professional", "student",
              "journalist", "writer", "editor", "publicist", "strategist",
              "freelance", "graduate", "candidate", "supervisor", "lead",
              "president", "founder", "owner", "partner", "advisor")
# street and place words that make an address line look like a name
ADDRESS_WORDS = {"rd", "road", "st", "street", "ave", "avenue", "blvd", "dr",
                 "drive", "lane", "ln", "court", "crt", "cres", "way", "unit",
                 "apt", "suite", "floor", "toronto", "ontario", "canada",
                 "vancouver", "mississauga", "brampton", "hamilton", "ottawa",
                 "on", "bc", "ab", "qc", "usa", "india", "box"}


def looks_like_name(line):
    line = re.sub(r'\([^)]*\)?', ' ', line)          # strip "(GIGI" and similar
    line = line.split("|")[0].split(",")[0]
    s = re.sub(r'[^A-Za-zÀ-ɏ\'\- ]', ' ', line).strip()
    s = re.sub(r'^\s*[Bb]y\s+', '', s)
    s = re.sub(r'\s+', ' ', s)
    if not (4 <= len(s) <= 44):
        return None
    parts = s.split(" ")
    if not (2 <= len(parts) <= 4):
        return None
    low = s.lower()
    if parts[0].lower() in SALUTATION:
        return None
    if any(p.lower() in HEADING_WORDS for p in parts):
        return None
    if any(p.lower() in ADDRESS_WORDS for p in parts):
        return None
    if any(w in low for w in ROLE_WORDS):
        return None
    if any(p.lower() in STOP_TOKENS for p in parts):
        return None
    ok = 0
    for p in parts:
        if len(p) < 2:
            return None
        if p[0].isupper() or p.isupper():
            ok += 1
    if ok < len(parts):
        return None
    return " ".join(w.capitalize() if w.isupper() else w for w in parts)


def name_from_text(text):
    for line in (text or "").split("\n")[:12]:
        n = looks_like_name(line.strip())
        if n:
            return n
    return None


def name_from_filename(fn):
    base = os.path.splitext(os.path.basename(fn))[0]
    base = re.sub(r'[_\-.]+', ' ', base)
    base = re.sub(r'\(\d+\)', ' ', base)
    ARTICLES = {"the", "a", "an", "and", "for", "of", "to", "my", "at", "in"}
    toks = [t for t in re.split(r'\s+', base) if t and t.lower() not in STOP_TOKENS
            and t.lower() not in ARTICLES and not t.isdigit()]
    if len(toks) >= 2:
        return looks_like_name(" ".join(toks[:3]))
    return None


def name_matches_email(name, addr):
    """True when the email local part contains a chunk of the name."""
    if not name or not addr:
        return False
    local = re.sub(r'[^a-z]', '', addr.split("@")[0].lower())
    if len(local) < 4:
        return False
    parts = name.split() if " " in name else [name]
    for p in parts:
        p = re.sub(r'[^a-z]', '', p.lower())
        if len(p) >= 5 and (p in local or local in p):
            return True
    return False


def name_quality(n, addr=None):
    """Higher is better. Prefers a complete, properly capitalised human name."""
    if not n:
        return -1
    parts = [p for p in n.split() if p]
    if len(parts) < 2:
        return 0
    score = 10 + min(len(parts), 2)
    proper = sum(1 for p in parts if p[:1].isupper() and not p.isupper())
    score += proper * 3
    if n.isupper() or n.islower():
        score -= 4
    edge = [parts[0], parts[-1]]
    if any(len(p) == 1 or (len(p) == 2 and p.endswith(".")) for p in edge):
        score -= 3          # leading or trailing initial, such as "G Benj"
    score += min(len(n), 30) / 20.0
    if name_matches_email(n, addr):
        score += 12
    return score


def tidy_name(n):
    if not n:
        return n
    if n.isupper() or n.islower():
        return " ".join(w.capitalize() for w in n.split())
    return n


def norm_key(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    return re.sub(r'[^a-z]', '', s)


def pick_email(text, exclude_domains=()):
    found = EMAIL_RE.findall(text or "")
    out = []
    for e in found:
        e = e.strip(".,;:").lower()
        dom = e.split("@")[-1]
        if any(d in dom for d in exclude_domains):
            continue
        out.append(e)
    return out[0] if out else None


# ---------------------------------------------------------------- collection
def collect_files(root):
    """Yield (path, origin) for every candidate document, expanding .eml."""
    items, emails_seen = [], []
    tmpdir = tempfile.mkdtemp(prefix="screen-applicants-")
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in sorted(filenames):
            if fn.startswith("."):
                continue
            p = os.path.join(dirpath, fn)
            ext = os.path.splitext(fn)[1].lower()
            if ext == ".eml":
                items.extend(expand_eml(p, tmpdir, emails_seen))
            elif ext in DOC_EXT:
                items.append({"path": p, "display": fn, "origin": "file", "group": None})
            elif ext in SKIP_EXT:
                items.append({"path": p, "display": fn, "origin": "skipped", "group": None})
            else:
                items.append({"path": p, "display": fn, "origin": "skipped", "group": None})
    return items, emails_seen, tmpdir


def expand_eml(path, tmpdir, emails_seen):
    out = []
    try:
        with open(path, "rb") as fh:
            m = email.message_from_binary_file(fh, policy=policy.default)
    except Exception:
        return [{"path": path, "display": os.path.basename(path),
                 "origin": "skipped", "group": None}]
    frm = str(m.get("From", ""))
    disp = frm.split("<")[0].strip().strip('"')
    addr = None
    ma = EMAIL_RE.search(frm)
    if ma:
        addr = ma.group(0).lower()
    gid = "eml:" + (addr or os.path.basename(path))
    body = ""
    for part in m.walk():
        if part.get_content_type() == "text/plain" and not part.get_filename():
            try:
                body = part.get_content(); break
            except Exception:
                pass
    body = re.split(r'\n-{2,}\s*Forwarded message', norm(body or ""))[0].strip()
    sub = os.path.join(tmpdir, re.sub(r'[^A-Za-z0-9]+', '-', gid)[:60])
    os.makedirs(sub, exist_ok=True)
    if body:
        bp = os.path.join(sub, "_email-note.txt")
        open(bp, "w").write(body)
        out.append({"path": bp, "display": "Email note", "origin": "eml",
                    "group": gid, "sender_name": disp, "sender_email": addr,
                    "forced_kind": "Email note"})
    idx = 0
    for part in m.walk():
        fn = part.get_filename()
        if not fn:
            continue
        idx += 1
        safe = re.sub(r'[/\\]', "_", fn)
        dest = os.path.join(sub, "%02d-%s" % (idx, safe))
        try:
            open(dest, "wb").write(part.get_payload(decode=True) or b"")
        except Exception:
            continue
        if os.path.splitext(safe)[1].lower() in DOC_EXT:
            out.append({"path": dest, "display": safe, "origin": "eml",
                        "group": gid, "sender_name": disp, "sender_email": addr})
        else:
            out.append({"path": dest, "display": safe, "origin": "skipped", "group": gid})
    return out


# ---------------------------------------------------------------- main
def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    items, _, tmpdir = collect_files(src)

    docs, skipped = [], []
    for it in items:
        if it["origin"] == "skipped":
            skipped.append({"file": it["display"], "reason": "unsupported file type"})
            continue
        text, mode = to_text(it["path"])
        if not text or len(text.strip()) < 40:
            skipped.append({"file": it["display"],
                            "reason": "no extractable text (%s)" % mode})
            continue
        if it.get("forced_kind"):
            kind, is_app, conf = it["forced_kind"], True, 1.0
        else:
            kind, is_app, conf = classify(text, it["display"])
            # anything attached to an application email is part of that application
            if it["origin"] == "eml" and kind != "not-an-application":
                is_app, conf = True, max(conf, 0.6)
        rec = {"file": it["display"], "kind": kind, "text": text, "mode": mode,
               "confidence": conf, "is_app": is_app, "group": it.get("group"),
               "sender_name": it.get("sender_name"), "sender_email": it.get("sender_email"),
               "email": pick_email(text)}
        if kind in ("Reference letter", "Writing sample", "Portfolio"):
            rec["name"] = name_from_filename(it["display"]) or name_from_text(text)
            rec["name_for_display"] = False
        else:
            rec["name"] = name_from_text(text) or name_from_filename(it["display"])
            rec["name_for_display"] = True
        rec["from_resume"] = (kind == "Resume")
        docs.append(rec)

    # ---- collapse byte-identical documents that appear more than once
    # (a zip often holds both an .eml and its already-extracted attachments)
    import hashlib
    bysig = {}
    for d in docs:
        sig = hashlib.sha1(re.sub(r"\s+", " ", d["text"]).strip().encode()).hexdigest()
        keep = bysig.get(sig)
        if keep is None:
            bysig[sig] = d
            continue
        # same document twice: keep the copy carrying identity, pool the rest
        for f in ("group", "sender_name", "sender_email", "email", "name"):
            if not keep.get(f) and d.get(f):
                keep[f] = d[f]
        if d["is_app"] and not keep["is_app"]:
            keep["is_app"], keep["kind"] = True, d["kind"]
        d["duplicate_of"] = sig
    docs = [d for d in docs if "duplicate_of" not in d]

    # ---- group into candidates
    groups = {}
    def key_for(d):
        if d.get("group"):
            return d["group"]
        if d.get("email"):
            return "email:" + d["email"]
        if d.get("name"):
            return "name:" + norm_key(d["name"])
        return "file:" + d["file"]

    for d in docs:
        if not d["is_app"]:
            continue
        groups.setdefault(key_for(d), []).append(d)

    # merge groups that share an email address or a name
    merged, index = [], {}
    for gid, ds in groups.items():
        emails = {d["email"] for d in ds if d.get("email")}
        emails |= {d["sender_email"] for d in ds if d.get("sender_email")}
        names = {norm_key(d["name"]) for d in ds if d.get("name")}
        names |= {norm_key(d["sender_name"]) for d in ds if d.get("sender_name")}
        g = {"docs": list(ds), "emails": {e for e in emails if e},
             "names": {n for n in names if n}, "gid": gid}
        merged.append(g)

    # pass 1: union groups that share an email address
    by_email, kept = {}, []
    for g in merged:
        target = None
        for e in g["emails"]:
            if e in by_email:
                target = by_email[e]; break
        if target is None:
            kept.append(g); target = g
        else:
            target["docs"].extend(g["docs"])
            target["emails"] |= g["emails"]
            target["names"] |= g["names"]
        for e in target["emails"]:
            by_email.setdefault(e, target)

    # pass 1b: same person using more than one address, linked by name
    def disp_names(g):
        out = set()
        for d in g["docs"]:
            for v in (d.get("name"), d.get("sender_name")):
                k = norm_key(v)
                if k and len(k) > 6:
                    out.add(k)
        return out

    changed = True
    while changed:
        changed = False
        for i, a in enumerate(kept):
            if a is None:
                continue
            for j in range(i + 1, len(kept)):
                b = kept[j]
                if b is None:
                    continue
                na, nb = disp_names(a), disp_names(b)
                same_name = bool(na & nb)
                cross = False
                for g1, g2 in ((a, b), (b, a)):
                    for e in g2["emails"]:
                        for n in disp_names(g1):
                            if name_matches_email(n, e) and len(n) > 6:
                                cross = True
                if same_name or cross:
                    a["docs"].extend(b["docs"])
                    a["emails"] |= b["emails"]
                    a["names"] |= b["names"]
                    kept[j] = None
                    changed = True
        kept = [g for g in kept if g is not None]

    # pass 2: groups with no email attach to a named group when the name matches
    by_name = {}
    for g in kept:
        if g["emails"]:
            for n in g["names"]:
                by_name.setdefault(n, g)
    final = []
    for g in kept:
        if g["emails"]:
            final.append(g); continue
        host = None
        for n in g["names"]:
            if n in by_name:
                host = by_name[n]; break
        if host is not None:
            host["docs"].extend(g["docs"])
            host["names"] |= g["names"]
        else:
            final.append(g)
    merged = final

    ORDER = {"Email note": 0, "Cover letter": 1, "Resume": 2}
    candidates, unnamed = [], 0
    for g in merged:
        addr = None
        for d in g["docs"]:
            addr = d.get("sender_email") or d.get("email")
            if addr:
                break
        options = []
        for d in g["docs"]:
            if d.get("name") and d.get("name_for_display", True):
                options.append((name_quality(d["name"], addr) + (4 if d.get("from_resume") else 0),
                                tidy_name(d["name"])))
        for d in g["docs"]:
            if d.get("sender_name"):
                options.append((name_quality(tidy_name(d["sender_name"]), addr) - 1,
                                tidy_name(d["sender_name"])))
        options.sort(key=lambda x: -x[0])
        disp = options[0][1] if options and options[0][0] > 0 else None
        if not disp:
            unnamed += 1
            disp = "Unidentified %d" % unnamed
        seen, dl = set(), []
        for d in sorted(g["docs"], key=lambda d: ORDER.get(d["kind"], 3)):
            sig = (d["kind"], d["text"][:120])
            if sig in seen:
                continue
            seen.add(sig)
            dl.append({"label": d["kind"], "file": d["file"],
                       "text": d["text"], "mode": d["mode"]})
        candidates.append({"name": disp, "email_address": addr, "documents": dl})

    candidates.sort(key=lambda c: c["name"])
    json.dump(candidates, open(os.path.join(dst, "candidates.json"), "w"),
              indent=1, ensure_ascii=False)

    low = [{"file": d["file"], "kind": d["kind"], "confidence": d["confidence"]}
           for d in docs if not d["is_app"]]
    report = {
        "input_folder": os.path.abspath(src),
        "files_seen": len(items),
        "documents_extracted": len(docs),
        "application_documents": sum(len(c["documents"]) for c in candidates),
        "candidates_found": len(candidates),
        "unidentified_candidates": unnamed,
        "not_application_documents": low,
        "skipped_files": skipped,
        "review_these": [c["name"] for c in candidates if c["name"].startswith("Unidentified")]
                        + [c["name"] for c in candidates if len(c["documents"]) > 6],
    }
    json.dump(report, open(os.path.join(dst, "report.json"), "w"), indent=1, ensure_ascii=False)

    print("candidates:      %d" % len(candidates))
    print("app documents:   %d" % report["application_documents"])
    print("set aside:       %d not applications, %d unreadable/unsupported"
          % (len(low), len(skipped)))
    if unnamed:
        print("NEEDS REVIEW:    %d candidate(s) with no name found" % unnamed)
    print("\nwrote %s/candidates.json and report.json" % dst)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
