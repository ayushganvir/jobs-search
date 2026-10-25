#!/usr/bin/env python3
"""joblog.py: the ONLY way to write job status into applied_log.jsonl (validated, timestamped, one application per company).

  python3 joblog.py add  --company C --title T --status S [--note N] [--url U] [--tab ID] [--channel CH] [--force] [--keep-tab]
  python3 joblog.py show <company>      every log row for a company (oldest first) and the current status
  python3 joblog.py open                everything waiting on Ayush, with Go-to-tab links
  python3 joblog.py check               lint the log (bad JSON, unknown statuses, missing fields, two applications at one company)

Statuses: submitted | confirmed | interview | rejected | offer | needs_user | blocked | skipped | withdrawn | superseded.
Rules enforced by `add`:
  - status must be one of the above; company and title required; needs_user/blocked need a --note saying what Ayush must do.
  - one application per company: a second `submitted` for a company that already has a different submitted role is refused
    unless --force.
  - every row gets date (today) and ts (ISO seconds); the newest row wins (tracker/sync.py orders by position in the file).
  - a final status (submitted/confirmed/skipped/...) with --tab closes that Chrome tab (unless --keep-tab); then sync.py runs.
"""
import argparse, datetime, json, pathlib, subprocess, sys
J = pathlib.Path(__file__).resolve().parent
LOG = J / "applied_log.jsonl"
sys.path.insert(0, str(J))
import chrome_tabs as ct

STATUSES = ("submitted", "confirmed", "interview", "rejected", "offer", "needs_user", "blocked", "skipped", "withdrawn",
            "superseded", "unconfirmed")
APPLIED = {"submitted", "confirmed", "interview", "rejected", "offer"}
LEGACY = {"queued"}  # old rows written before joblog.py; tolerated by `check`, refused by `add`

def rows():
    out = []
    if LOG.exists():
        for i, l in enumerate(LOG.read_text().splitlines()):
            if not l.strip():
                continue
            try:
                out.append((i + 1, json.loads(l)))
            except ValueError:
                out.append((i + 1, None))
    return out

def latest():
    cur = {}
    for _, r in rows():
        if not r:
            continue
        k = (ct.norm(r.get("company")), ct.norm(r.get("title")))
        if r.get("status") == "superseded":
            cur.pop(k, None)
        else:
            cur[k] = r
    return cur

def add(a):
    if a.status not in STATUSES:
        sys.exit(f"unknown status {a.status!r}; use one of {', '.join(STATUSES)}")
    if not a.company.strip() or not a.title.strip():
        sys.exit("--company and --title are required")
    if a.status in ("needs_user", "blocked") and not (a.note or "").strip():
        sys.exit("needs_user/blocked rows need --note with the exact step Ayush must do")
    nc, nt = ct.norm(a.company), ct.norm(a.title)
    if a.status == "submitted" and not a.force:
        other = [r for (c, t), r in latest().items() if c == nc and t != nt and r.get("status") in APPLIED]
        if other:
            sys.exit(f"{a.company} already has an application ({other[0].get('title')!r}, {other[0].get('status')}); "
                     "one per company. Use the same --title to update it, or --force.")
    now = datetime.datetime.now()
    row = {"company": a.company.strip(), "title": a.title.strip(), "status": a.status, "date": now.date().isoformat(),
           "ts": now.isoformat(timespec="seconds"), "note": (a.note or "").strip()}
    if a.url:
        row["url"] = a.url
    if a.tab:
        row["where"] = f"tab {a.tab}"
    if a.channel:
        row["channel"] = a.channel
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")
    msg = f"logged {row['company']} / {row['title']}: {row['status']}"
    if a.tab and a.status not in ("needs_user", "blocked", "unconfirmed") and not a.keep_tab:
        msg += f"; closed tab {a.tab}" if ct.close([a.tab]) else f"; tab {a.tab} was not open"
    subprocess.run([sys.executable, str(J / "tracker" / "sync.py")], capture_output=True)
    print(msg)

def show(company):
    nc = ct.norm(company)
    hits = [(n, r) for n, r in rows() if r and (ct.norm(r.get("company")) == nc or (len(nc) > 3 and nc in ct.norm(r.get("company"))))]
    for n, r in hits:
        print(f"line {n}: {r.get('date')} {r.get('status'):11} {r.get('company')} / {r.get('title')}  {r.get('note', '')[:70]}")
    cur = [r for (c, t), r in latest().items() if c == nc or (len(nc) > 3 and nc in c)]
    print("current:", "; ".join(f"{r.get('title')} = {r.get('status')}" for r in cur) or "not in the log")

def open_items():
    """Everything waiting on Ayush, exactly as the dashboard shows it (tracker/data.json after a fresh sync)."""
    subprocess.run([sys.executable, str(J / "tracker" / "sync.py")], capture_output=True)
    home = json.loads((J / "tracker" / "data.json").read_text()).get("home", {})
    items = home.get("needs", []) + home.get("needs_signin", [])
    for r in items:
        tid = r.get("tab_id") or ""
        print(f"- {r.get('company')} / {r.get('title')}: {r.get('note', '')[:90]}  [{'tab ' + tid if tid else 'no tab open'}] {r.get('go', '')}")
    print(f"{len(items)} waiting on Ayush")

def check():
    problems, applied_by_co = 0, {}
    for n, r in rows():
        if r is None:
            print(f"line {n}: not valid JSON"); problems += 1; continue
        if r.get("status") not in STATUSES and r.get("status") not in LEGACY:
            print(f"line {n}: unknown status {r.get('status')!r} ({r.get('company')})"); problems += 1
        for f in ("company", "title", "status", "date"):
            if not r.get(f):
                print(f"line {n}: missing {f} ({r.get('company')})"); problems += 1
    for (c, t), r in latest().items():
        if r.get("status") in APPLIED:
            applied_by_co.setdefault(c, []).append(r.get("title"))
    for c, ts in applied_by_co.items():
        if len(ts) > 1:
            print(f"note: {len(ts)} applications at {c}: {ts}")
    print(f"{len(rows())} rows, {problems} problems")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add")
    for f in ("--company", "--title", "--status"):
        s.add_argument(f, required=True)
    for f in ("--note", "--url", "--tab", "--channel"):
        s.add_argument(f)
    s.add_argument("--force", action="store_true")
    s.add_argument("--keep-tab", action="store_true")
    sub.add_parser("show").add_argument("company")
    sub.add_parser("open")
    sub.add_parser("check")
    a = p.parse_args()
    {"add": lambda: add(a), "show": lambda: show(a.company), "open": open_items, "check": check}[a.cmd]()
