#!/usr/bin/env python3
"""make_queue.py: merge candidates.json (freehire) + extra_candidates.json (ATS boards, feeds) into today_queue.json,
which tracker/sync.py shows as 'queued' and the auto-apply runs work from.
Rules: one role per company; skip companies/urls already in applied_log.jsonl; keep still-pending jobs from the old queue;
order: no-account forms first, then captcha, then account portals; Hyderabad, Mumbai, Bengaluru, remote, Pune/Chennai/NCR, rest of India; by score. Telegram reposts are left out."""
import json, re, datetime as dt
from pathlib import Path
import build_candidates as bc
HERE = Path(__file__).parent
QUEUE = HERE / "today_queue.json"
EASY_ATS = {"greenhouse", "ashby", "lever", "workable", "freshteam", "recruitee", "keka", "smartrecruiters"}
ACCOUNT_ATS = {"workday", "oracle", "successfactors", "taleo", "icims"}

def kind_of(src, url):
    s = (src or "").lower(); u = (url or "").lower()
    if "zohorecruit" in u or s == "zohorecruit": return "captcha"
    if s in EASY_ATS or any(k in u for k in ("greenhouse", "ashbyhq", "lever.co", "workable", "freshteam", "recruitee", "keka")): return "easy"
    if s in ACCOUNT_ATS or any(k in u for k in ("myworkdayjobs", "oraclecloud", "successfactors", "taleo")): return "account"
    return "other"

CITIES = ("hyderabad|secunderabad", "mumbai|navi mumbai|thane", "bengaluru|bangalore", "remote|anywhere",
          "pune|chennai|gurgaon|gurugram|noida|delhi|ncr")  # Ayush relocates anywhere in India (2026-10-21): rest of India ranks last

def city_rank(loc):
    l = (loc or "").lower()
    for i, c in enumerate(CITIES):
        if re.search(c, l): return i
    return len(CITIES)

EXTRA_BAD = re.compile(r"investment|partner|research|reliability|\bbi\b|power ?bi|tableau|graduates?|glue|computer vision|mandarin|japanese|german|french|pathologist|labview|netsuite|freshers?|heat exchanger|director|consultant|physical design|c\+\+|\.net|\blead\b|drive \d|therapist|urdu|speech &|dot ?net|sugarcrm|associate software|big data|electronics|ontolog", re.I)
MAX_ACCOUNT = 30  # account portals cost Ayush a sign-in each; keep only the best ones queued

def attempted_all():
    urls, cos = bc.attempted()
    for l in (HERE / "applied_log.jsonl").read_text().splitlines():  # skipped companies stay out too
        try: r = json.loads(l)
        except ValueError: continue
        if r.get("status") == "skipped": cos.add(bc._norm(r.get("company")))
    cos |= {bc._norm(a) for a in bc.APPLIED}
    return urls, cos

def main():
    if (HERE / "PAUSED").exists():  # applying is paused: keep an empty queue so nothing is worked or counted as pending
        QUEUE.write_text(json.dumps({"date": str(dt.date.today()), "paused": (HERE / "PAUSED").read_text().strip(), "jobs": []}, indent=1))
        print("queue: paused (jobs/PAUSED exists), 0 jobs")
        return []
    a_urls, a_cos = attempted_all()
    old = json.loads(QUEUE.read_text()).get("jobs", []) if QUEUE.exists() else []
    pool = []
    for j in old:  # carry over jobs not yet attempted
        if j.get("url", "").split("?")[0] not in a_urls and bc._norm(j.get("company")) not in a_cos:
            pool.append(j)
    try:
        for c in json.loads((HERE / "candidates.json").read_text()):
            pool.append({"company": c["company"], "title": c["title"], "location": c.get("location", ""), "source": c.get("source", ""),
                         "kind": c.get("kind") or kind_of(c.get("source"), c["url"]), "url": c["url"], "hyd": c.get("hyd", False), "score": c.get("score", 0)})
    except (OSError, ValueError): pass
    try:
        for e in json.loads((HERE / "extra_candidates.json").read_text()):
            t, co = e.get("title", ""), e.get("company", "")
            if bc.BAD_TITLE.search(t) or bc.BAD_CO.search(co): continue
            s = max([w for p, w in bc.GOOD_TITLE if re.search(p, t.lower())] or [0])
            if not s: continue
            pool.append({"company": co, "title": t, "location": e.get("loc", ""), "source": e.get("ats", ""),
                         "kind": kind_of(e.get("ats"), e.get("url")), "url": e["url"].split("?")[0],
                         "hyd": bool(re.search(r"hyderabad|secunderabad", e.get("loc", ""), re.I)), "score": s + (3 if re.search(r"hyderabad", e.get("loc", ""), re.I) else 0)})
    except (OSError, ValueError): pass
    order = {"easy": 0, "captcha": 1, "account": 2, "other": 3}
    pool.sort(key=lambda j: (order.get(j.get("kind"), 3), city_rank(j.get("location")), -(j.get("score") or 0)))
    out, cos, n_acc = [], set(), 0
    for j in pool:
        nc = bc._norm(j.get("company"))
        if not nc or nc in cos or nc in a_cos or j["url"].split("?")[0] in a_urls: continue
        if any(len(a) > 4 and (a in nc or nc in a) for a in a_cos): continue  # e.g. 'guidewiresoftwaresolutions...' vs 'guidewire'
        if bc.BAD_TITLE.search(j.get("title", "")) or EXTRA_BAD.search(j.get("title", "")): continue
        if re.search(r"europe|usa|canada|united states|\buk\b", j.get("location") or "", re.I) and not re.search(r"india|worldwide|anywhere", j.get("location") or "", re.I): continue  # not open to India
        if (j.get("source") or "") == "telegram": continue  # Telegram reposts of LinkedIn jobs were mostly closed (Ayush, 2026-10-21)
        if j.get("kind") == "account":
            if n_acc >= MAX_ACCOUNT: continue
            n_acc += 1
        cos.add(nc); j["plan"] = "queue"; out.append(j)
    QUEUE.write_text(json.dumps({"date": str(dt.date.today()), "jobs": out}, indent=1))
    from collections import Counter
    print(f"queue: {len(out)} jobs", dict(Counter(j['kind'] for j in out)))
    return out

if __name__ == "__main__":
    main()
