#!/usr/bin/env python3
"""
Build the screening board from scored candidates.

    python3 build.py <scored.json> <config.json> <output.html>

scored.json   the candidates.json produced by extract.py, with scoring fields added
config.json   role, axes, tiers, filters and page copy
output.html   written here, ready to publish as an artifact

Every candidate in scored.json must have a tier that exists in the config, and a
score for every axis. The script refuses to build if anything is missing, so a
half-scored batch never reaches the board.
"""
import sys, os, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")


def die(msg):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(1)


def main(scored_path, config_path, out_path):
    cands = json.load(open(scored_path, encoding="utf-8"))
    cfg = json.load(open(config_path, encoding="utf-8"))

    # two different people can share a display name; documents are keyed by
    # name, so make names unique before anything else touches them
    seen_names = {}
    for c in cands:
        n = c.get("name") or "Unnamed"
        if n in seen_names:
            seen_names[n] += 1
            c["name"] = "%s (%d)" % (n, seen_names[n])
        else:
            seen_names[n] = 1

    axes = cfg.get("axes") or []
    if not axes:
        die("config has no axes")
    tier_keys = {t["key"] for t in cfg.get("tiers", [])}
    if not tier_keys:
        die("config has no tiers")

    # ---- validate before building
    problems = []
    for c in cands:
        n = c.get("name", "?")
        if not c.get("tier"):
            problems.append("%s has no tier" % n)
        elif c["tier"] not in tier_keys:
            problems.append("%s has tier %r which is not in the config" % (n, c["tier"]))
        s = c.get("scores") or {}
        for a in axes:
            v = s.get(a["key"])
            if v is None:
                problems.append("%s has no %s score" % (n, a["key"]))
            elif not (isinstance(v, int) and 1 <= v <= 5):
                problems.append("%s has %s = %r, expected an integer 1 to 5" % (n, a["key"], v))
    if problems:
        print("Cannot build. %d problem(s):" % len(problems), file=sys.stderr)
        for p in problems[:25]:
            print("  " + p, file=sys.stderr)
        if len(problems) > 25:
            print("  ... and %d more" % (len(problems) - 25), file=sys.stderr)
        sys.exit(1)

    # ---- split the payload: board data stays small, documents go in their own map
    C, DOCS = [], {}
    for c in cands:
        name = c["name"]
        rec = {"t": c["tier"], "n": name, "loc": c.get("location", ""),
               "s": {a["key"]: c["scores"][a["key"]] for a in axes},
               "now": c.get("current", ""), "why": c.get("assessment", ""),
               "watch": c.get("watch", "")}
        if c.get("decide_first"):
            rec["flag"] = c["decide_first"]
        tags = c.get("tags") or []
        if tags:
            rec["tags"] = [t if isinstance(t, list) else [t, ""] for t in tags]
        C.append(rec)
        docs = c.get("documents") or []
        DOCS[name] = {
            "email": c.get("email_address") or "",
            "docs": [{"l": d.get("label", "Document"), "t": d.get("text", ""),
                      "m": d.get("mode", "flow"),
                      **({"f": d["file"]} if d.get("file") else {})}
                     for d in docs],
        }

    order = {t["key"]: i for i, t in enumerate(cfg["tiers"])}
    C.sort(key=lambda r: (order.get(r["t"], 99),
                          -sum(r["s"].get(a["key"], 0) for a in axes), r["n"]))

    # ---- counts the page shows
    counts = {}
    for r in C:
        counts[r["t"]] = counts.get(r["t"], 0) + 1
    ndocs = sum(len(v["docs"]) for v in DOCS.values())
    cfg.setdefault("stats", [])
    if not cfg["stats"]:
        cfg["stats"] = [{"n": len(C), "l": "Applied"}]
        for t in cfg["tiers"][:2]:
            if counts.get(t["key"]):
                cfg["stats"].append({"n": counts[t["key"]], "l": t.get("stat_label", t["title"])})
        cfg["stats"].append({"n": ndocs, "l": "Documents"})

    tpl = open(TEMPLATE, encoding="utf-8").read()

    title = cfg.get("title") or ("%s Screening" % cfg.get("role", "Applicant"))
    tpl = tpl.replace("__TITLE__", title.replace("<", "").replace(">", ""), 1)

    for token, value in (("__CONFIG__", cfg), ("__DOCS__", DOCS), ("__CANDIDATES__", C)):
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        payload = payload.replace("</script>", "<\\/script>")
        if token not in tpl:
            die("template is missing %s" % token)
        tpl = tpl.replace(token, payload, 1)

    open(out_path, "w", encoding="utf-8").write(tpl)
    kb = os.path.getsize(out_path) / 1024
    print("built %s" % out_path)
    print("  candidates: %d   documents: %d   size: %.0f KB" % (len(C), ndocs, kb))
    for t in cfg["tiers"]:
        if counts.get(t["key"]):
            print("  %-28s %d" % (t["title"], counts[t["key"]]))
    if kb > 15000:
        print("  WARNING: over the 16 MB artifact limit; trim document text")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
