#!/usr/bin/env python3
"""chrome_tabs.py: see and clean up Ayush's Chrome job tabs (macOS AppleScript; tab ids = the Control_Chrome tool ids).

  python3 chrome_tabs.py list            every tab: id, kind, matched company + its log status, URL
  python3 chrome_tabs.py cleanup [--dry] close tabs that are no longer needed (see CLOSE RULES), print what was closed
  python3 chrome_tabs.py close <id> ...  close specific tabs

Kinds: protected (Gmail, dashboard, YouTube, anything not job-related: never closed), helper (tab-jump / apply-with-LinkedIn
pop-ups), done (a confirmation page by URL), job (an ATS / job-board page), other.
CLOSE RULES (cleanup): helper tabs; done pages; job tabs whose company's latest log status is final (submitted, confirmed,
interview, rejected, offer, skipped) and that have no open (needs_user/blocked) row; duplicate job tabs with the same URL
(the first one is kept); extra dashboard tabs (one is kept). Tabs of companies that still need Ayush are never closed.
"""
import json, re, subprocess, sys, pathlib
J = pathlib.Path(__file__).resolve().parent
LOG = J / "applied_log.jsonl"

FINAL = {"submitted", "confirmed", "interview", "rejected", "offer", "skipped"}
OPEN = {"needs_user", "blocked", "unconfirmed"}
JOB_HOSTS = ("myworkdayjobs.com", "myworkdaysite.com", "successfactors.", "icims.com", "oraclecloud.com", "greenhouse.io",
             "lever.co", "ashbyhq.com", "workable.com", "smartrecruiters.com", "zohorecruit", "keka.com", "freshteam.com",
             "recruitee.com", "talemetry.com", "jobvite.com", "ttcportals.com", "himalayas.app", "linkedin.com/jobs",
             "naukri.com/job-listings", "phenompeople", "docs.google.com/forms", "-recruit.", "pinpointhq.com", "careers.", "jobs.", "/careers", "/jobs/")
ATS_HOSTS = ("oraclecloud.com", "myworkdayjobs.com", "myworkdaysite.com", "successfactors", "icims.com", "greenhouse.io",
             "lever.co", "ashbyhq.com", "workable.com", "smartrecruiters.com", "zohorecruit", "keka.com", "freshteam.com",
             "recruitee.com", "talemetry.com", "jobvite.com", "pinpointhq.com", "docs.google.com", "linkedin.com", "indeed.com",
             "wellfound.com", "naukri.com", "himalayas.app")
HELPER = ("127.0.0.1:8787/go", "linkedin.com/talentwidgets", "about:blank")
DONE_URL = (r"/jobTasks/completed/application", r"keka\.com/careers/success/", r"[?&]success\b", r"/job_app/confirmation", r"mode=submit_apply", r"docs\.google\.com/forms/.*/formResponse",
            r"/apply/.*(thank|success|confirmation)", r"/(thank-?you|application-submitted|confirmation)(\b|/|\?)")
PROTECT = (r"mail\.google\.com", r"youtube\.com", r"chatgpt\.com", r"claude\.ai", r"dash\.cloudflare\.com",
           r"linkedin\.com/(feed|notifications|messaging|in/)", r"naukri\.com/mnjuser", r"accounts\.google\.com")
DASHBOARD = ("jobs.ayush.cc", "127.0.0.1:8787/")

SCRIPT_LIST = ('tell application "System Events" to if not (exists process "Google Chrome") then return ""\n'
               'tell application "Google Chrome"\nset out to ""\nrepeat with w in windows\nrepeat with t in tabs of w\n'
               'set out to out & (id of t) & "\t" & (URL of t) & "\t" & (title of t) & linefeed\nend repeat\nend repeat\n'
               'return out\nend tell')
SCRIPT_CLOSE = '''on run argv
  set closed to 0
  tell application "Google Chrome"
    repeat with i in argv
      repeat with w in windows
        try
          close (first tab of w whose id is (i as integer))
          set closed to closed + 1
          exit repeat
        end try
      end repeat
    end repeat
  end tell
  return closed
end run'''

def tabs():
    """[(id, url, title)] of every open Chrome tab; [] if Chrome is closed or AppleScript fails."""
    out = ""
    for _ in range(2):  # Chrome can be slow to answer while pages load: wait up to 30 s, retry once
        try:
            out = subprocess.run(["osascript", "-e", SCRIPT_LIST], capture_output=True, text=True, timeout=30).stdout
        except Exception:
            out = ""
        if out.strip():
            break
    return [tuple((l.split("\t") + ["", ""])[:3]) for l in out.splitlines() if l.strip()]

def close(ids):
    ids = [str(i) for i in ids if str(i).strip()]
    if not ids:
        return 0
    r = subprocess.run(["osascript", "-", *ids], input=SCRIPT_CLOSE, capture_output=True, text=True, timeout=20)
    try:
        return int((r.stdout or "0").strip())
    except ValueError:
        return 0

def norm(s):
    s = re.sub(r"\b(llc|inc|ltd|labs|pvt|private|limited|technologies|the)\b", "", (s or "").lower())
    return re.sub(r"[^a-z0-9]", "", s)

def companies():
    """{norm company: {"name", "final", "open", "urls"}} using the newest-wins rule of tracker/sync.py: a company is
    open only if an open row (needs_user/blocked) was written after its last applied/skipped row."""
    latest = {}
    if LOG.exists():
        for i, l in enumerate(LOG.read_text().splitlines()):
            try:
                r = json.loads(l)
            except ValueError:
                continue
            r["_seq"] = i
            k = (norm(r.get("company")), norm(r.get("title")))
            if r.get("status") == "superseded":
                latest.pop(k, None)
            else:
                latest[k] = r
    out = {}
    for (nc, _), r in latest.items():
        if not nc:
            continue
        c = out.setdefault(nc, {"name": r.get("company"), "final_seq": -1, "open_seq": -1, "urls": []})
        if r.get("status") in FINAL:
            c["final_seq"] = max(c["final_seq"], r["_seq"])
        if r.get("status") in OPEN:
            c["open_seq"] = max(c["open_seq"], r["_seq"])
        if r.get("url"):
            c["urls"].append(r["url"].split("?")[0].rstrip("/"))
    for c in out.values():
        c["open"] = c["open_seq"] > c["final_seq"]
        c["final"] = c["final_seq"] >= 0 and not c["open"]
    return out

def kind(url):
    u = url or ""
    if any(h in u for h in HELPER):
        return "helper"
    if any(re.search(p, u) for p in PROTECT):
        return "protected"
    if any(d in u for d in DASHBOARD):
        return "dashboard"
    if any(re.search(p, u, re.I) for p in DONE_URL):
        return "done"
    if any(h in u for h in JOB_HOSTS):
        return "job"
    return "other"

def match(url, title, cos):
    """company key for a job tab: exact URL first, then company name in the URL host/path or the tab title."""
    base = (url or "").split("?")[0].rstrip("/")
    for nc, c in cos.items():
        for u in c["urls"]:  # same job URL; prefix match only for long, job-specific paths (not ".../careers")
            if u and (u == base or (min(len(u), len(base)) >= 50 and (base.startswith(u) or u.startswith(base)))):
                return nc
    host, _, path = base.split("//")[-1].partition("/")
    # on shared ATS hosts (oraclecloud.com, greenhouse.io, ...) the host names the vendor, not the employer: an
    # "oracle" company must not match every Oracle-hosted careers tab (closed EXL's form once), so use path + title only
    hay = norm((path if any(h in host for h in ATS_HOSTS) else base.split("//")[-1]) + " " + (title or ""))
    best = ""
    for nc in cos:
        if len(nc) >= 4 and nc in hay and len(nc) > len(best):
            best = nc
    return best

def plan(all_tabs=None):
    """[(id, url, kind, company, action, reason)] for every tab; action is 'close' or 'keep'."""
    all_tabs = tabs() if all_tabs is None else all_tabs
    cos = companies()
    rows, seen_url, dash_kept = [], set(), False
    for tid, url, title in all_tabs:
        k = kind(url)
        nc = match(url, title, cos) if k in ("job", "done") else ""
        c = cos.get(nc, {})
        action, why = "keep", ""
        if k == "helper":
            action, why = "close", "helper tab"
        elif k == "dashboard":
            action, why = ("close", "extra dashboard tab") if dash_kept else ("keep", "dashboard")
            dash_kept = True
        elif k == "done":
            action, why = ("keep", "confirmation, but company still has an open item") if c.get("open") else ("close", "confirmation page")
        elif k == "job":
            key = url.split("#")[0]
            if key in seen_url:
                action, why = "close", "duplicate tab"
            elif c.get("final") and not c.get("open"):
                action, why = "close", "company finished in the log"
            else:
                why = "needs Ayush" if c.get("open") else ("not in the log" if not nc else "in progress")
            seen_url.add(key)
        else:
            why = k
        rows.append((tid, url, k, c.get("name", ""), action, why))
    return rows

def cleanup(dry=False):
    rows = plan()
    ids = [r[0] for r in rows if r[4] == "close"]
    n = 0 if dry else close(ids)
    return rows, ids, n

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "close":
        print(f"closed {close(sys.argv[2:])}")
    elif cmd == "cleanup":
        dry = "--dry" in sys.argv
        rows, ids, n = cleanup(dry)
        for tid, url, k, co, act, why in rows:
            if act == "close":
                print(f"{'would close' if dry else 'closed'} {tid}  [{why}]  {co}  {url[:90]}")
        print(f"{'dry run: ' if dry else ''}{len(ids)} to close, {n} closed, {len(rows) - len(ids)} kept")
    else:
        for tid, url, k, co, act, why in plan():
            print(f"{tid}\t{k:9}\t{act:5}\t{why[:28]:28}\t{co[:22]:22}\t{url[:90]}")
