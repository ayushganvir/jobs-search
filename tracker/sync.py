#!/usr/bin/env python3
"""Merge applied_log.jsonl + gmail_status.json -> data.json. Re-runnable."""
import json, re, pathlib, datetime, collections, subprocess, urllib.parse
HERE = pathlib.Path(__file__).resolve().parent
LOG = HERE.parent / "applied_log.jsonl"
GM = HERE / "gmail_status.json"
OUT = HERE / "data.json"
JOBS = HERE.parent
CAND = JOBS / "candidates.json"
DIGESTS = JOBS / "digests"
APPLIED = {"submitted", "unconfirmed", "confirmed", "interview", "rejected"}

# Catalog from jobs/sources.md. key = candidates.json "source" (or extra-digest tag) it maps to.
# (key, name, type, status, access, friction, rating, note)
CATALOG = [
 ("freehire", "freehire", "aggregator", "in use", "API (daily.py)", "mixed", "High", "Primary aggregator; every candidate in candidates.json comes through it."),
 ("greenhouse", "Greenhouse boards", "ATS board", "in use", "Public JSON API + direct form", "no account", "High", "Best signal: AI/voice startups; curated slug list in extra_sources.py adds freshness."),
 ("lever", "Lever boards", "ATS board", "in use", "Public JSON API + direct form", "no account", "High", "Documented public postings API; unknown slug = 404."),
 ("ashby", "Ashby boards", "ATS board", "in use", "Public JSON API + direct form", "no account", "High", "Sarvam, Certa, Cursor etc.; direct no-account forms."),
 ("keka", "Keka careers", "ATS board", "in use", "Public careers JSON (embedjobs) + form", "no account", "Medium", "Indian HR/ATS; curated slugs in extra_sources.py (Fynd, Niyo, Minfy, Keka...)."),
 ("freshteam", "Freshteam careers", "ATS board", "in use", "Public careers HTML + form", "no account", "Medium", "Indian startups (Cashflo, Zolve, RemoteStar...); no dates on cards."),
 ("recruitee", "Recruitee boards", "ATS board", "in use", "Public offers API + form", "no account", "Low", "Mostly EU; few India companies."),
 ("jooble", "Jooble India", "aggregator", "in use", "Free API (key)", "mixed", "Medium", "Aggregates Indian boards; links redirect via Jooble."),
 ("smartrecruiters", "SmartRecruiters", "ATS board", "in use", "Public postings API + form", "no account", "Medium", "Freshworks, Sia etc.; usually no account."),
 ("workable", "Workable", "ATS board", "in use", "v3 accounts API (one at a time, rate-limited) + form", "no account", "Medium", "24 India accounts incl. Weekday, Innovaccer, Exponent, Lokal, DeepSource."),
 ("workday", "Workday job lists", "ATS board", "in use", "Public cxs JSON (no login to list)", "account needed", "Medium", "47 tech/product companies (Cisco, NVIDIA, eBay, Qualys, HPE, Mastercard...); apply needs a per-company account."),
 ("reddit", "r/developersIndia hiring posts", "community", "in use", "Search RSS (JSON is 403)", "varies", "Low", "Few real hiring posts; strict title filter."),
 ("hnjobs", "HN job ads (YC companies)", "community", "in use", "Algolia tags=job", "no account", "Low", "YC startup ads naming India; rare."),
 ("himalayas", "Himalayas", "job board", "in use", "Free JSON API (filter locationRestrictions)", "account needed", "Medium", "Remote/India-eligible AI and founding roles; link back to Himalayas."),
 ("remotive", "Remotive", "job board", "in use", "Public JSON API", "no account", "Low-Medium", "Few India-eligible, mostly senior/EU; ~4 calls/day."),
 ("remoteok", "RemoteOK", "job board", "planned", "Public JSON API", "no account", "Low", "Mostly US-timezone; attribution required."),
 ("wwr", "WeWorkRemotely", "job board", "planned", "RSS", "no account", "Low", "Few India-eligible; trivial RSS add."),
 ("hn", "HN Who is hiring", "community", "in use", "Algolia API (monthly)", "no account", "Medium", "Founder-posted, email apply; best for founding/FDE roles."),
 ("startupjobs", "startup.jobs", "job board", "in use", "via freehire only (RSS is 403)", "account needed", "Covered", "Cloudflare-walled directly; freehire already pulls it."),
 ("telegram", "Telegram channels", "community", "in use", "via freehire", "account needed", "Medium", "Posts surfaced by freehire; mostly links to account-gated ATS."),
 ("yc", "YC company list (slug discovery)", "community", "in use", "yc-oss JSON, weekly", "n/a", "Medium", "India + hiring YC cos probed on Greenhouse/Lever/Ashby; results feed those boards."),
 ("github-lists", "GitHub awesome lists", "community", "planned", "GitHub search API", "n/a", "Medium", "Seed company names, then probe ATS slugs."),
 ("funding", "Funding lists (Entrackr/Inc42/Tracxn)", "community", "planned", "Manual / RSS", "n/a", "Medium", "Weekly manual seed: freshly funded India AI startups."),
]
NOT_USABLE = [
 ("Naukri", "job board", "Redirect + Akamai anti-bot SPA, no API", "account needed", "Prohibits scraping; huge but noisy, many body shops."),
 ("LinkedIn Jobs", "job board", "Guest endpoint rate-limits fast", "account needed", "ToS bans scraping and automation; Easy Apply needs login."),
 ("Indeed India (scraping)", "job board", "RSS removed (404); JobSpy needs bot-evasion", "account needed", "Bans scraping; used only inside Ayush's signed-in Chrome (see Chrome sources)."),
 ("Foundit", "job board", "SPA, no API", "account needed", "ToS; no programmatic access."),
 ("Wellfound", "job board", "Turnstile bot-wall, no public API", "account needed", "Prohibits scraping."),
 ("Instahyre", "job board", "403 Cloudflare challenge", "account needed", "Bot-walled."),
 ("Y Combinator Work at a Startup", "job board", "406 to curl, no public API", "account needed", "Login-gated; manual only."),
 ("Cutshort", "job board", "Next.js app, no public API", "account needed", "Scraping not permitted; login to apply."),
 ("Hirist", "job board", "SPA, no public API", "account needed", "Scrape risk, OTP/account."),
 ("Arc.dev / Welcome to the Jungle", "job board", "SPA, no public API", "account needed", "Remote-global / mostly Europe."),
 ("JobSpy", "tool", "pip package scraping the walled sites", "n/a", "Same ToS/IP-block risk; lead discovery only."),
]
# map apply-URL host fragments to source keys
HOSTS = [("greenhouse.io", "greenhouse"), ("lever.co", "lever"), ("ashbyhq.com", "ashby"),
         ("smartrecruiters.com", "smartrecruiters"), ("workable.com", "workable"), ("himalayas.app", "himalayas"),
         ("zohorecruit", "zohorecruit"), ("keka.com", "keka"), ("freshteam.com", "freshteam"), ("recruitee.com", "recruitee"), ("myworkdayjobs.com", "workday"), ("oraclecloud.com", "oracle")]

def build_sources(apps_rows):
    cands = json.loads(CAND.read_text()) if CAND.exists() else []
    by_src = collections.Counter(c.get("source") for c in cands)
    kinds_by_src = collections.defaultdict(collections.Counter)
    for c in cands:
        kinds_by_src[c.get("source")][c.get("kind")] += 1
    comp2src = {}
    for c in cands:
        comp2src[norm(c.get("company", ""))] = c.get("source")
    extra = collections.Counter()
    if DIGESTS.exists():
        for f in DIGESTS.glob("extra_*.md"):
            for line in f.read_text().splitlines():
                m = re.match(r"- \*\*.*\*\* .* · (\w[\w-]*)\s*$", line)
                if m:
                    extra[m.group(1)] += 1
                    comp = re.match(r"- \*\*.*?\*\* — (.*?) ·", line)
                    if comp:
                        comp2src.setdefault(norm(comp.group(1)), m.group(1))
    applied = collections.Counter()
    unattr = 0
    for r in apps_rows:
        if r["status"] not in APPLIED:
            continue
        key = None
        for l in r["links"]:
            host = urllib.parse.urlparse(l).netloc.lower() if str(l).startswith("http") else ""
            for frag, k in HOSTS:
                if frag in host:
                    key = k; break
            if key: break
        if not key:
            key = comp2src.get(norm(r["company"] or ""))
        if key:
            applied[key] += 1
        else:
            unattr += 1
    total_applied = sum(applied.values()) + unattr
    known = {c[0] for c in CATALOG}
    out = []
    for key, name, typ, status, access, fr, rating, note in CATALOG:
        n = len(cands) if key == "freehire" else by_src.get(key, 0)
        a = total_applied if key == "freehire" else applied.get(key, 0)
        out.append({"key": key, "name": name, "type": typ, "status": status, "access": access, "friction": fr,
                    "rating": rating, "candidates": n, "curated_found": extra.get(key, 0), "applied": a,
                    "note": note, "group": "main"})
    for src, n in by_src.most_common():
        if src in known:
            continue
        k = kinds_by_src[src].most_common(1)[0][0]
        fr = {"easy": "no account", "captcha": "captcha", "account": "account needed"}.get(k, "unknown")
        out.append({"key": src, "name": src, "type": "ATS board", "status": "in use", "access": "via freehire (ATS form)",
                    "friction": fr, "rating": "-", "candidates": n, "curated_found": extra.get(src, 0),
                    "applied": applied.get(src, 0), "note": "ATS seen in freehire results; not individually researched.",
                    "group": "other_ats"})
    for name, typ, access, fr, note in NOT_USABLE:
        out.append({"key": name.lower(), "name": name, "type": typ, "status": "evaluated-not-usable", "access": access,
                    "friction": fr, "rating": "Low (skip)", "candidates": 0, "curated_found": 0, "applied": 0,
                    "note": note, "group": "not_usable"})
    cs = read_json(JOBS / "chrome_sites.json", {})
    for site, label in (("naukri", "Naukri"), ("linkedin", "LinkedIn"), ("wellfound", "Wellfound"), ("indeed", "Indeed"),
                        ("workday", "Workday company portals"), ("oracle", "Oracle company portals")):
        info = cs.get(site, {}) if isinstance(cs, dict) else {}
        n = sum(1 for a in apps_rows if a.get("site") == site and a["status"] in APPLIED)
        out.append({"key": "chrome-" + site, "name": label, "type": "chrome", "status": info.get("status", "unknown"),
                    "access": "user's own Chrome session", "friction": "account needed", "rating": "-",
                    "candidates": 0, "curated_found": 0, "applied": n, "note": info.get("note", ""), "group": "chrome"})
    kc = collections.Counter(c.get("kind") for c in cands)
    summary = {"total_candidates": len(cands), "by_kind": dict(kc), "total_applied": total_applied,
               "applied_unattributed": unattr, "curated_extra_total": sum(extra.values())}
    return out, summary

def norm(s):
    s = re.sub(r"\b(llc|inc|ltd|labs|pvt|private|limited|technologies|the)\b", "", s.lower())
    return re.sub(r"[^a-z0-9]", "", s)

QUEUE = JOBS / "today_queue.json"
STMAP = {"submitted": "submitted", "confirmed": "submitted", "unconfirmed": "submitted", "interview": "submitted",
         "rejected": "submitted", "skipped": "skipped", "needs_user": "needs your action", "blocked": "blocked"}

SITE_HOSTS = [("myworkdayjobs", "workday"), ("oraclecloud", "oracle"), ("greenhouse.io", "greenhouse"), ("lever.co", "lever"),
              ("ashbyhq", "ashby"), ("naukri", "naukri"), ("linkedin", "linkedin"), ("wellfound", "wellfound"), ("indeed.com", "indeed"),
 ("smartrecruiters", "smartrecruiters"), ("zohorecruit", "zohorecruit"), ("keka.com", "keka"), ("freshteam.com", "freshteam"), ("recruitee.com", "recruitee"), ("workable", "workable")]

def site_of(url):
    h = urllib.parse.urlparse(url or "").netloc.lower()
    for f, k in SITE_HOSTS:
        if f in h:
            return k
    return ""

def read_json(p, default):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default

def infer_mode(text):
    t = (text or "").lower()
    if "remote" in t or "work from home" in t or "wfh" in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    if re.search(r"on-?site|in-?office|work from office", t):
        return "On-site"
    return "Not stated"

_META = None
def meta_for(company, title="", url=""):
    """location + work_mode: manual job_meta.json first, then candidates/today_queue, else Not stated."""
    global _META
    if _META is None:
        manual = read_json(JOBS / "job_meta.json", {})
        by_co = {norm(k): v for k, v in manual.items()}
        pool = []
        for p, key in ((JOBS / "candidates.json", None), (QUEUE, "jobs")):
            d = read_json(p, [])
            pool += d.get(key, []) if key and isinstance(d, dict) else (d if isinstance(d, list) else [])
        _META = (by_co, pool)
    by_co, pool = _META
    nc, nt = norm(company or ""), norm(title or "")
    for j in pool:
        if (url and j.get("url") and j["url"].split("?")[0] == url.split("?")[0]) or \
           (norm(j.get("company", "")) == nc and nt and (norm(j.get("title", "")) in nt or nt in norm(j.get("title", "")))):
            loc = j.get("location") or ""
            mode = infer_mode(loc + " " + (j.get("title") or ""))
            if j.get("remote") and mode == "Not stated":
                mode = "Remote"
            m = by_co.get(nc, {})
            return m.get("location") or loc or "", (m.get("work_mode") if m.get("work_mode") and m["work_mode"] != "Not stated" else mode)
    m = by_co.get(nc)
    if m:
        return m.get("location", ""), m.get("work_mode", "Not stated")
    return "", "Not stated"

def badge_of(where, channel, url):
    if (where or "").upper().startswith("YOUR CHROME") or channel == "chrome":
        return "chrome"
    if where:
        return "browser"
    return "link"

_TABS = None
def chrome_tabs():
    """[(tab_id, url, title)] of every open Chrome tab (AppleScript; same ids as the Control_Chrome tools). [] if Chrome is closed."""
    global _TABS
    if _TABS is None:
        scr = ('tell application "System Events" to if not (exists process "Google Chrome") then return ""\n'
               'tell application "Google Chrome"\nset out to ""\nrepeat with w in windows\nrepeat with t in tabs of w\n'
               'set out to out & (id of t) & "\t" & (URL of t) & "\t" & (title of t) & linefeed\nend repeat\nend repeat\nreturn out\nend tell')
        try:
            r = subprocess.run(["osascript", "-e", scr], capture_output=True, text=True, timeout=10).stdout
            _TABS = [tuple((l.split("\t") + ["", ""])[:3]) for l in r.splitlines() if l.strip()]
        except Exception:
            _TABS = []
    return _TABS

def tab_for(company, url):
    """Chrome tab id holding this job: same URL path first, else company name in the tab's URL host/path or title."""
    base = (url or "").split("?")[0].rstrip("/")
    for tid, u, t in chrome_tabs():
        tb = u.split("?")[0].rstrip("/")
        if base and (tb == base or (len(base) >= 50 and tb.startswith(base[:60]))):  # short URLs like ".../careers" match many tabs
            return tid
    key = re.sub(r"[^a-z0-9]", "", re.sub(r"\b(inc|llc|ltd|pvt|technologies|group|partners|labs)\b", "", (company or "").lower().split("(")[-1]))
    if len(key) < 3: return ""
    for tid, u, t in chrome_tabs():
        hay = re.sub(r"[^a-z0-9]", "", (u.split("?")[0] + " " + t).lower())
        if key in hay and not re.search(r"mail\.google|linkedin\.com/(feed|notifications)|naukri\.com/mnjuser", u):
            return tid
    return ""

PRIO = {1: "Interview / assessment", 2: "Quick submit", 3: "Needs your answers", 4: "Sign in / setup"}
def classify_action(note, status):
    n = (note or "").lower()
    if status == "interview" or "interview" in n or "assessment" in n: return 1, "Interview"
    if re.search(r"sign.?in|create account|log.?in|verify (your )?(phone|email)", n): return 4, "Sign in"
    if re.search(r"captcha|recaptcha|click submit|submit application|apply now|attach (the )?resume|tick", n) and not re.search(r"answer|\?|references|marks|%|rate|which|how many", n): return 2, "Submit"
    return 3, "Answer"

def build_actions(apps, needs, signin):
    """One prioritised list for the dashboard's 'Your actions' card: interviews first, then quick submits,
    then forms waiting on Ayush's answers, then sign-ins / setup tasks (incl. manual ones in jobs/actions.json)."""
    out = []
    recent = (datetime.date.today() - datetime.timedelta(days=21)).isoformat()
    for a in apps:
        if a["status"] == "interview" and (a.get("last_update") or "") >= recent:
            link = next((l for l in reversed(a["links"]) if "mail.google" in str(l)), "") or next((l for l in a["links"] if str(l).startswith("http")), "")
            out.append({"priority": 1, "kind": "Interview", "company": a["company"], "title": a["title"],
                        "detail": "Interview / assessment invite: complete it (see the email)", "go": link, "tab_id": ""})
    for r in needs + signin:
        u = (r.get("url") or "")
        if r.get("status") == "blocked":
            continue  # Claude retries these (site down etc.); not Ayush's to do
        if re.search(r"indeed\.com|naukri\.com|wellfound\.com", u) and not r.get("tab_id"):
            pr, kind = 4, "Via FINISH_DRAFTS prompt"  # finished by the Claude-in-Chrome finish-drafts run
        else:
            pr, kind = classify_action(r.get("note"), r.get("status"))
        out.append({"priority": pr, "kind": kind, "company": r["company"], "title": r["title"], "detail": r.get("note", ""),
                    "go": r.get("go") if r.get("tab_id") else (r.get("url") or r.get("go")), "tab_id": r.get("tab_id", "")})
    for t in read_json(JOBS / "actions.json", []):
        if not t.get("done"):
            out.append({"priority": int(t.get("priority", 4)), "kind": t.get("kind", "Task"), "company": t.get("title", ""),
                        "title": "", "detail": t.get("detail", ""), "go": t.get("link", ""), "tab_id": ""})
    out.sort(key=lambda x: (x["priority"], x["kind"], x["company"] or ""))
    for x in out:
        x["priority_label"] = PRIO.get(x["priority"], "")
    return out

def build_home(apps, today):
    needs, signin = [], []
    for a in apps:
        if a["status"] not in ("needs_user", "blocked"):
            continue
        link = next((l for l in a["links"] if str(l).startswith("http")), "")
        row = {"company": a["company"], "title": a["title"], "status": a["status"], "note": a.get("note", ""),
               "url": link, "site": a.get("site", ""), "channel": a.get("channel", "pane"),
               "where": a.get("where", ""), "badge": badge_of(a.get("where", ""), a.get("channel", "pane"), link)}
        tid = tab_for(a["company"], link)
        row["tab_id"] = tid
        row["go"] = "http://127.0.0.1:8787/go?" + urllib.parse.urlencode({"tab": tid, "u": link})  # opens/focuses the exact tab
        if re.search(r"sign.?in|create account|log.?in", row["note"], re.I):
            row["portal"] = row["site"] or "portal"
            signin.append(row)
        else:
            needs.append(row)
    c = collections.Counter(r["status"] for r in today)
    tot = len(today)
    running = read_json(JOBS / "running.json", [])
    ch = collections.Counter(a.get("channel", "pane") for a in apps if a["status"] in APPLIED)
    return {"needs": needs, "needs_signin": signin, "actions": build_actions(apps, needs, signin),
            "totals": {"submitted": c["submitted"], "skipped": c["skipped"], "needs_you": len(needs) + len(signin),  # same list the Needs-you card shows
                       "queued": c["queued"], "total": c["submitted"] + c["skipped"] + len(needs) + len(signin) + c["queued"]},
            "all_time": {"applied": sum(1 for a in apps if a["status"] in APPLIED_ST), "needs_you": len(needs) + len(signin),
                         "confirmed": sum(1 for a in apps if a["status"] in ("confirmed", "interview"))},
            "running": running if isinstance(running, list) else [],
            "channels": {k: ch.get(k, 0) for k in ("pane", "chrome", "email")}}

def build_today(apps):
    q = json.loads(QUEUE.read_text()) if QUEUE.exists() else {"date": "", "jobs": []}
    day = q.get("date", "")
    used, rows = set(), []
    def fin(a):
        return a["status"]
    seen_q, qjobs = set(), []
    for j in q.get("jobs", []):
        k = (norm(j.get("company", "")), norm(j.get("title", "")))
        if k not in seen_q:
            seen_q.add(k); qjobs.append(j)
    for j in qjobs:
        nc, nt = norm(j.get("company", "")), norm(j.get("title", ""))
        same_co = sum(1 for x in qjobs if norm(x.get("company", "")) == nc)
        def title_ok(a):
            at = norm(a["title"] or "")
            return bool(nt) and (at == nt or at in nt or nt in at)
        cand = [i for i, a in enumerate(apps)
                if (j.get("url") and j["url"] in a["links"])
                or (norm(a["company"] or "") == nc and (title_ok(a) or same_co == 1))]
        best = None
        for i in cand:
            a = apps[i]
            sc = (j.get("url") in a["links"] if j.get("url") else 0, norm(a["title"] or "") == nt, a["last_update"])
            if best is None or sc > best[0]:
                best = (sc, i)
        status, note, ch, site, where = "queued", "", "pane", j.get("source") or "", ""
        if best:
            used.add(best[1]); a = apps[best[1]]
            status, note = STMAP.get(a["status"], "queued"), a.get("note", "")
            where = a.get("where", "")
            ch, site = a.get("channel", "pane"), a.get("site") or site
        _l, _m = meta_for(j.get("company"), j.get("title"), j.get("url", ""))
        rows.append({"company": j.get("company"), "title": j.get("title"), "location": j.get("location") or _l, "work_mode": _m,
                     "source": j.get("source"), "friction": j.get("kind"), "hyd": bool(j.get("hyd")),
                     "channel": ch, "site": site, "where": where, "badge": badge_of(where, ch, j.get("url")), "plan": j.get("plan"), "score": j.get("score"), "status": status, "note": note, "url": j.get("url")})
    for i, a in enumerate(apps):
        if i in used or a.get("log_date") != day:
            continue
        link = next((l for l in a["links"] if str(l).startswith("http")), "")
        rows.append({"company": a["company"], "title": a["title"], "location": a.get("location", ""), "work_mode": a.get("work_mode", "Not stated"), "source": "", "friction": "",
                     "hyd": False, "channel": a.get("channel", "pane"), "site": a.get("site", ""), "where": a.get("where", ""), "badge": badge_of(a.get("where", ""), a.get("channel", "pane"), link), "plan": "logged_today", "score": None,
                     "status": STMAP.get(a["status"], "queued"), "note": a.get("note", ""), "url": link})
    return rows

APPLIED_ST = ("submitted", "confirmed", "interview", "rejected", "offer")
OPEN_ST = ("needs_user", "blocked", "unconfirmed")

def collapse(out):
    """One truth per company: an open row is dropped when the same company has an applied row written AFTER it
    (position in applied_log.jsonl, so a later correction back to needs_user wins), and duplicate open rows for a
    company (title spelled differently) keep only the newest."""
    applied_on = {}
    for a in out:
        if a["status"] in APPLIED_ST:
            nc = norm(a["company"] or "")
            applied_on[nc] = max(applied_on.get(nc, -1), a.get("seq", -1))
    keep, open_seen = [], set()
    for a in sorted(out, key=lambda x: x.get("seq", -1), reverse=True):
        nc = norm(a["company"] or "")
        if a["status"] in OPEN_ST:
            if nc in applied_on and applied_on[nc] > a.get("seq", -1):
                continue
            if nc in open_seen:
                continue
            open_seen.add(nc)
        keep.append(a)
    keep.sort(key=lambda x: x["last_update"], reverse=True)
    return keep

def main():
    rows = []
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            r["_seq"] = len(rows)  # file order = time order; the newest row wins
            rows.append(r)
    mails = json.loads(GM.read_text()) if GM.exists() else []
    apps = {}  # latest log row per company+title wins
    for r in rows:
        k = (norm(r.get("company", "")), norm(r.get("title", "")))
        if r.get("status") == "superseded":
            apps.pop(k, None)  # retired duplicate row
            continue
        apps[k] = r
    out = []
    for (nc, _), r in apps.items():
        links = [r["url"]] if r.get("url") else []
        status, last, signals = r.get("status", ""), r.get("date", ""), []
        ms = [m for m in mails if norm(m["company"]) == nc or (nc and (nc in norm(m["company"]) or norm(m["company"]) in nc))]
        for m in sorted(ms, key=lambda m: m.get("date", "")):
            if m.get("role") and norm(m["role"]) != norm(r.get("title", "")) and norm(m["role"]) not in norm(r.get("title", "")):
                continue
            c = m["classification"]
            signals.append(c)
            links.append(m["viewUrl"])
            last = max(last, m.get("date", ""))
            if c == "confirmed" and status in ("unconfirmed", "needs_user", "blocked", "skipped", ""):
                status = "confirmed"
            elif c == "confirmed" and status == "submitted":
                status = "confirmed"
            elif c in ("interview", "assessment"):
                status = "interview"
            elif c == "rejected":
                status = "rejected"
        loc, mode = meta_for(r.get("company"), r.get("title"), r.get("url", ""))
        out.append({"company": r.get("company"), "title": r.get("title"), "location": loc, "work_mode": mode, "status": status,
                    "channel": r.get("channel") or "pane", "where": r.get("where", ""), "site": r.get("site") or site_of(r.get("url", "")), "log_status": r.get("status"), "log_date": r.get("date", ""), "seq": r["_seq"], "last_update": last, "note": r.get("note", ""),
                    "gmail_signals": signals, "links": links})
    out.sort(key=lambda x: x["last_update"], reverse=True)
    out = collapse(out)
    sources, summary = build_sources(out)
    today = [r for r in build_today(out) if r.get("status") != "skipped"]  # skipped jobs stay in the log (so they are not retried) but are hidden from the dashboard
    out = [x for x in out if x["status"] != "skipped"]
    for r in out + today:  # every row waiting on Ayush gets a link that focuses its filled Chrome tab
        if r.get("status") in ("needs_user", "blocked", "needs your action"):
            u = r.get("url") or next((l for l in r.get("links", []) if str(l).startswith("http")), "")
            tid = tab_for(r.get("company"), u)
            r["tab_id"], r["go"] = tid, "http://127.0.0.1:8787/go?" + urllib.parse.urlencode({"tab": tid, "u": u})
    OUT.write_text(json.dumps({"generated": datetime.datetime.now().isoformat(timespec="seconds"), "applications": out,
                               "sources": sources, "source_summary": summary, "today": today, "home": build_home(out, today)}, indent=1))
    print(f"wrote {len(out)} applications")

if __name__ == "__main__":
    main()
