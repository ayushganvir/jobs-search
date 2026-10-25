#!/usr/bin/env python3
"""reconcile.py: clear 'needs you' rows once a confirmation/interview/rejection email exists.
Input (stdin, JSON list): [{"company","role","classification":"confirmed|interview|assessment|rejected","date","viewUrl","subject","jobIds":["210790233"]}]
Optional per mail: "add_if_missing": true and "channel": "linkedin" -> append a new row when no row for that company exists.
jobIds = job/requisition numbers read from the email subject/body; they are matched against the job URL in applied_log (most reliable).
Updates tracker/gmail_status.json and appends rows to applied_log.jsonl, then runs tracker/sync.py.
Usage: reconcile.py [--dry] < mails.json   (prints a JSON summary of what changed)"""
import json, re, sys, subprocess, pathlib
J = pathlib.Path(__file__).resolve().parent
LOG, GM = J / "applied_log.jsonl", J / "tracker" / "gmail_status.json"
DRY = "--dry" in sys.argv
def norm(s):
    s = re.sub(r"\b(llc|inc|ltd|labs|pvt|private|limited|technologies|systems|software|the|ai|partners)\b", "", (s or "").lower())
    return re.sub(r"[^a-z0-9]", "", s)
def toks(s): return {t for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(t) > 2}
rows = []
for l in LOG.read_text().splitlines():
    try: rows.append(json.loads(l))
    except ValueError: pass
latest = {}
for r in rows:
    latest[(norm(r.get("company")), norm(r.get("title")))] = r
latest = {k: r for k, r in latest.items() if r.get("status") != "superseded"}
OPEN = {"needs_user", "blocked", "unconfirmed", "submitted", "skipped"}  # a receipt email beats an earlier 'skipped'
gm = json.loads(GM.read_text()) if GM.exists() else []
if "--known" in sys.argv:  # thread ids already reconciled: the scheduled task skips these instead of re-reading them
    print(" ".join(sorted({m["viewUrl"].split("thread-f:")[-1].split("|")[0] for m in gm if "thread-f:" in (m.get("viewUrl") or "")})))
    sys.exit()
mails = json.load(sys.stdin)
seen = {(norm(m["company"]), m.get("viewUrl")) for m in gm}
changed, appended = [], []
for m in mails:
    nc = norm(m["company"]); cls = m.get("classification", "confirmed")
    if not nc: continue
    if (nc, m.get("viewUrl")) not in seen:
        gm.append({"company": m["company"], "role": m.get("role", ""), "classification": cls, "date": m.get("date", ""), "viewUrl": m.get("viewUrl", "")}); seen.add((nc, m.get("viewUrl")))
    ids = [str(i) for i in m.get("jobIds", []) if len(str(i)) >= 5]
    by_id = [r for r in latest.values() if r.get("status") in OPEN and any(i in (r.get("url") or "") for i in ids)] if ids else []
    cand = by_id or [r for (c, t), r in latest.items() if (c == nc or (nc and (nc in c or c in nc))) and r.get("status") in OPEN - {"skipped"}]  # 'skipped' flips only on a job-number match
    if len(cand) > 1 and not by_id:  # several roles at one company: prefer the one whose title words appear in the email
        mt = toks(m.get("subject", "") + " " + m.get("role", ""))
        best = [r for r in cand if toks(r.get("title")) & mt and len(toks(r.get("title")) & mt) >= 2]
        cand = best or [r for r in cand if r.get("status") in ("needs_user", "blocked")][:1]
    new = {"confirmed": "submitted", "interview": "interview", "assessment": "interview", "rejected": "rejected"}.get(cls, "submitted")
    known = any(c == nc or (nc in c or c in nc) for (c, t) in latest)
    if not cand and not known and m.get("add_if_missing"):  # e.g. LinkedIn Easy Apply sent by the Claude-in-Chrome agents
        row = {"company": m["company"], "title": m.get("role") or "(applied via " + m.get("channel", "email") + ")", "status": new,
               "date": (m.get("date") or "")[:10], "note": f"added from email ({cls}): {m.get('subject','')[:80]}", "channel": m.get("channel", "email")}
        appended.append(row); changed.append(f'{m["company"]}: new -> {new}')
        latest[(nc, norm(row["title"]))] = row
        continue
    for r in cand:
        if r["status"] == new or (new == "submitted" and r["status"] == "submitted"): continue
        row = {"company": r["company"], "title": r["title"], "status": new, "date": (m.get("date") or "")[:10] or r.get("date", ""),
               "note": f"auto-reconciled from email ({cls}): {m.get('subject','')[:80]}", "channel": r.get("channel", "pane")}
        if r.get("url"): row["url"] = r["url"]
        appended.append(row); changed.append(f'{r["company"]}: {r["status"]} -> {new}')
if not DRY:
    with LOG.open("a") as f:
        for r in appended: f.write(json.dumps(r) + "\n")
    GM.write_text(json.dumps(gm, indent=1))
    subprocess.run([sys.executable, str(J / "tracker" / "sync.py")], capture_output=True)
print(json.dumps({"dry": DRY, "mails": len(mails), "cleared_or_updated": changed, "gmail_rows": len(gm)}))
