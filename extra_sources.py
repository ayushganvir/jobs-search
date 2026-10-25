#!/usr/bin/env python3
"""Extra India jobs (stdlib only): ATS board APIs for named companies (Greenhouse/Lever/Ashby/Keka/Freshteam/Recruitee,
plus slugs auto-discovered from the YC company list) + Himalayas + Remotive + HN Who-is-hiring + Jooble (if key set).
Writes jobs/digests/extra_YYYY-MM-DD.md and prints a count. No login, no bot-wall bypass."""
import json, os, re, subprocess, sys, time, datetime as dt, urllib.parse, urllib.request, concurrent.futures as cf
from pathlib import Path
HERE = Path(__file__).parent
MAX_AGE_DAYS = 30
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"
# verified live 2026-10-19 (slug -> returns jobs). Extend freely.
GH = "devrev nurix observeai prodigal simpplr slice truefoundry groww sigmoid bluestone databricks mongodb okta stripe twilio gitlab elastic datadog toast druva anthropic vercel inmobi hackerrank glance postman browserstack innovaccer chargebee freshworks".split()
LV = "cred meesho zeta mindtickle pocketfm levelai anyscale paytm hevodata fampay smallcase".split()
# India companies freehire lists on these ATSs (2026-10-19); keka "hr" = Keka itself (Hyderabad)
KK = "hr fynd niyo disprz adda247 cloudsufi minfy medhavi".split()
FT = "cashflo-talent zolve payatu cynlr zerodhafundhouse upswing remotestar-team udhyam quantela-team zimetrics".split()
RC = "greyparrotai".split()  # few India companies use Recruitee; extend when found
# Workday public job lists (host prefix, wdN, site) for tech/product companies freehire shows with India roles. Apply needs a Workday account.
WD = [x.split("|") for x in """cisco|wd5|Cisco_Careers salesforce|wd12|External_Career_Site mastercard|wd1|CorporateCareers visa|wd5|Visa nvidia|wd5|NVIDIAExternalCareerSite
intel|wd1|External hpe|wd5|Jobsathpe hp|wd5|ExternalCareerSite paloaltonetworks|wd5|panwexternalcareers autodesk|wd1|Ext ebay|wd5|apply expedia|wd108|search
priceline|wd1|Priceline cadence|wd1|External_Careers micron|wd1|External nxp|wd3|careers ciena|wd5|Careers motorolasolutions|wd5|Careers genesys|wd1|Genesys
equinix|wd1|External procore|wd12|Procore_External_Careers athenahealth|wd1|External modmed|wd501|India_Career_Site tricentis|wd1|Tricentis_Careers
clearwateranalytics|wd1|Clearwater_Analytics_Careers q2ebanking|wd5|Q2 fis|wd5|SearchJobs fiserv|wd5|EXT gartner|wd5|EXT lseg|wd3|Careers spgi|wd5|SPGI_Careers
blackrock|wd1|BlackRock_Professional ms|wd5|External citi|wd5|2 jiostar|wd102|JioStar saison|wd102|Credit_Saison_India qualys|wd5|Careers fractal|wd1|Careers
acronis|wd502|acronis_careers arcticwolf|wd1|External amadeus|wd502|jobs nationwide|wd1|Nationwide_Career_India equifax|wd5|External wexinc|wd5|WEXInc paypal|wd1|jobs target|wd5|targetcareers thomsonreuters|wd5|External_Career_Site db|wd3|DBWebsite barclays|wd3|External_Career_Site_Barclays chevron|wd5|jobs medtronic|wd1|MedtronicCareers warnerbros|wd5|global crowdstrike|wd5|crowdstrikecareers guidewire|wd5|external adobe|wd5|external_experienced broadcom|wd1|External_Career
jda|wd5|JDA_Careers adobe|wd5|external_experienced""".split()]
# Workable accounts with India roles (resolved from freehire apply links, 2026-10-19). weekday-1 = Weekday, posts many startup roles.
WK = """weekday-1 innovaccer-analytics exponent-energy lokal-app 2070health prox-works origin-10x proarch-3 docyt toloka-ai fortanix reveal-health-tech
qodeworld v2-ai deltaexchange wati-dot-i-o deepsource mercari-india seekho naehas rapyuta-robotics velsera 1kosmos botsync-1""".split()
YC_CACHE = HERE / "yc_slugs.json"  # refreshed weekly by discover_yc()
AB = "sarvam certa cursor elevenlabs deepgram livekit vapi bolna composio baseten fireworks modal replit supabase posthog atlan navi tekion anyscale level-ai openai".split()
CITY = re.compile(r"india|bengaluru|bangalore|hyderabad|secunderabad|mumbai|navi mumbai|thane|pune|gurgaon|gurugram|noida|chennai|delhi", re.I)
TITLE_OK = re.compile(r"voice|speech|conversational|forward.deployed|\bfde\b|founding|agent|llm|genai|generative|\brag\b|ai engineer|applied ai|ml engineer|machine learning|full.?stack|backend|back-end|python|django|golang|software (engineer|developer)|product engineer|solutions? engineer|platform engineer", re.I)
TITLE_BAD = re.compile(r"\b(intern|internship|trainee|fresher|junior|jr\.?|graduate|staff|principal|distinguished|vp|director|head of|manager|architect|sales|sdr|bdr|account|recruit|marketing|support|customer success|qa|sdet|devops|sre|data scientist|analyst|designer|ios|android|embedded|firmware|sap|salesforce|\.net|java|php|ruby|security|legal|finance|hr|contract)\b", re.I)

def get(url, as_json=True, data=None):
    h = {"User-Agent": UA, **({"Content-Type": "application/json"} if data else {})}
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h), timeout=25) as r:
        b = r.read()
    return json.loads(b) if as_json else b.decode()

def ok(title, loc):
    return bool(TITLE_OK.search(title)) and not TITLE_BAD.search(title) and bool(CITY.search(loc or ""))

def greenhouse(s):
    return [dict(company=s, title=j["title"], loc=j["location"]["name"], url=j["absolute_url"], posted=(j.get("first_published") or j.get("updated_at") or "")[:10], ats="greenhouse")
            for j in get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs")["jobs"]]
def lever(s):
    return [dict(company=s, title=j["text"], loc=" / ".join(j["categories"].get("allLocations") or [j["categories"].get("location") or ""]), url=j["hostedUrl"],
                 posted=dt.datetime.fromtimestamp(j["createdAt"]/1000, dt.timezone.utc).strftime("%Y-%m-%d"), ats="lever") for j in get(f"https://api.lever.co/v0/postings/{s}?mode=json")]
def ashby(s):
    out = []
    for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{s}")["jobs"]:
        loc = " / ".join([j.get("location") or ""] + [x.get("location", "") if isinstance(x, dict) else str(x) for x in j.get("secondaryLocations") or []])
        if j.get("isRemote"): loc += " remote"
        out.append(dict(company=s, title=j["title"], loc=loc, url=j["jobUrl"], posted=(j.get("publishedAt") or "")[:10], ats="ashby"))
    return out

def keka(s):
    page = get(f"https://{s}.keka.com/careers/", as_json=False)
    org = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", page).group(0)
    return [dict(company="keka" if s == "hr" else s, title=j["title"], loc=" / ".join(f"{l.get('city') or l.get('name')}, {l.get('countryName')}" for l in j.get("jobLocations") or []),
                 url=f"https://{s}.keka.com/careers/jobdetails/{j['id']}", posted=(j.get("publishedOn") or "")[:10], ats="keka")
            for j in get(f"https://{s}.keka.com/careers/api/embedjobs/default/active/{org}")]
def freshteam(s):
    page = get(f"https://{s}.freshteam.com/jobs", as_json=False)  # no JSON API; job cards carry data-portal-* attrs
    return [dict(company=s.split("-")[0], title=t.strip(), loc=loc, url=f"https://{s}.freshteam.com{href}", posted="", ats="freshteam")
            for href, loc, t in re.findall(r'<a href="(/jobs/[^"]+)"[^>]*data-portal-location="([^"]*)".*?class="job-title">([^<]+)<', page, re.S)]
def recruitee(s):
    return [dict(company=s, title=j["title"], loc=j.get("location") or j.get("country") or "", url=j["careers_url"], posted=(j.get("published_at") or "")[:10], ats="recruitee")
            for j in get(f"https://{s}.recruitee.com/api/offers/")["offers"]]

def workday(t):
    host, wd, site = t
    base = f"https://{host}.{wd}.myworkdayjobs.com"
    out = {}
    for q in ("python", "full stack", "ai engineer", "backend"):
        body = json.dumps({"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q}).encode()
        for j in get(f"{base}/wday/cxs/{host}/{site}/jobs", data=body).get("jobPostings", []):
            p = (j.get("postedOn") or "").lower()  # "Posted Today" / "Posted Yesterday" / "Posted 3 Days Ago" / "Posted 30+ Days Ago"
            n = 0 if "today" in p else 1 if "yesterday" in p else int((re.search(r"(\d+)", p) or [0, 99])[1]) + (1 if "+" in p else 0)
            out[j["externalPath"]] = dict(company=host, title=j["title"], loc=f"{j.get('locationsText', '')} {j['externalPath'].split('/')[2]}",
                                          url=f"{base}/en-US/{site}{j['externalPath']}", posted=str(dt.date.today() - dt.timedelta(days=n)), ats="workday")
    return list(out.values())
def workable(s):
    body = json.dumps({"query": "", "location": [], "department": [], "worktype": [], "remote": []}).encode()
    return [dict(company=s, title=j["title"], loc=", ".join(filter(None, [(j.get("location") or {}).get("city"), (j.get("location") or {}).get("country")])),
                 url=f"https://apply.workable.com/{s}/j/{j['shortcode']}/", posted=(j.get("published") or "")[:10], ats="workable")
            for j in get(f"https://apply.workable.com/api/v3/accounts/{s}/jobs", data=body).get("results", [])]

def reddit():
    """r/developersIndia hiring posts via search RSS (JSON API is 403 to scripts). Title must say hiring."""
    x = get("https://www.reddit.com/r/developersIndia/search.rss?q=hiring&restrict_sr=1&sort=new&t=month&limit=100", as_json=False)
    out = []
    for t, link, upd in re.findall(r'<entry>.*?<title>(.*?)</title>.*?<link href="(.*?)".*?<updated>(.*?)</updated>', x, re.S):
        t = re.sub(r"&amp;", "&", t)
        if re.search(r"\[hiring\]|^hiring\b|\bhiring:|\bwe.?re hiring\b|\bis hiring\b", t, re.I) and not re.search(r"freeze|layoff|\?$", t, re.I):
            out.append(dict(company="r/developersIndia", title=t, loc="see post", url=link, posted=upd[:10], ats="reddit"))
    return out
def hn_jobs():
    """HN 'job' stories (YC company ads); keep ones naming India or an Indian city."""
    return [dict(company=h["title"].split(" (YC")[0].split(" is hiring")[0].split(" Is Hiring")[0], title=h["title"], loc=h["title"],
                 url=h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}", posted=h["created_at"][:10], ats="hnjobs")
            for h in get("https://hn.algolia.com/api/v1/search_by_date?tags=job&hitsPerPage=200")["hits"] if CITY.search(h["title"])]

def discover_yc():
    """India-based, hiring YC companies -> which Greenhouse/Lever/Ashby slugs answer. Cached for 7 days."""
    try:
        c = json.loads(YC_CACHE.read_text())
        if c["date"] >= str(dt.date.today() - dt.timedelta(days=7)): return c
    except Exception: pass
    cos = [c for c in get("https://yc-oss.github.io/api/companies/all.json") if c.get("isHiring") and
           ("India" in (c.get("all_locations") or "") or any("India" in (r or "") for r in c.get("regions") or []))]
    probes = {"gh": "https://boards-api.greenhouse.io/v1/boards/{}", "lv": "https://api.lever.co/v0/postings/{}?limit=1", "ab": "https://api.ashbyhq.com/posting-api/job-board/{}"}
    tries = [(k, v) for c in cos for v in dict.fromkeys([c["slug"], re.sub(r"[^a-z0-9]", "", c["name"].lower())]) for k in probes]
    def hit(kv):
        try: get(probes[kv[0]].format(kv[1])); return kv
        except Exception: return None
    out = {"date": str(dt.date.today()), "gh": [], "lv": [], "ab": []}
    with cf.ThreadPoolExecutor(12) as ex:
        for r in ex.map(hit, tries):
            if r and r[1] not in out[r[0]]: out[r[0]].append(r[1])
    YC_CACHE.write_text(json.dumps(out, indent=1))
    print(f"YC discovery: {len(cos)} India hiring cos -> gh {len(out['gh'])}, lever {len(out['lv'])}, ashby {len(out['ab'])}", file=sys.stderr)
    return out

def secret(name):
    """Env var (JOOBLE_KEY ...) or macOS Keychain item with service <name>; None if absent."""
    v = os.environ.get(name.upper().replace("-", "_"))
    if v: return v
    r = subprocess.run(["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", name, "-w"], capture_output=True, text=True)
    return r.stdout.strip() or None

QUERIES = ("python developer", "full stack developer", "ai engineer", "llm engineer", "backend engineer", "voice ai", "forward deployed engineer", "founding engineer")
def jooble():
    key = secret("jooble-key")
    if not key: print("note: jooble skipped (no jooble-key)", file=sys.stderr); return []
    out = []
    for q in QUERIES:
        for j in get(f"https://jooble.org/api/{key}", data=json.dumps({"keywords": q, "location": "India"}).encode()).get("jobs", []):
            out.append(dict(company=j.get("company") or "?", title=re.sub(r"<[^>]+>", "", j["title"]), loc=j.get("location") or "",
                            url=j["link"], posted=(j.get("updated") or "")[:10], ats="jooble"))
    return out

def himalayas():
    out = []
    for q in ("python engineer", "full stack engineer", "ai engineer", "llm engineer", "voice ai", "forward deployed engineer", "founding engineer"):
        try:
            for j in get("https://himalayas.app/jobs/api/search?sort=recent&q=" + q.replace(" ", "%20")).get("jobs", []):
                lr = j.get("locationRestrictions") or []
                if lr and not any("india" in x.lower() for x in lr): continue  # empty = worldwide
                out.append(dict(company=j["companyName"], title=j["title"], loc="India" if lr else "Worldwide remote", url=j["applicationLink"].split("?")[0],
                                posted=dt.datetime.fromtimestamp(j["pubDate"], dt.timezone.utc).strftime("%Y-%m-%d") if isinstance(j.get("pubDate"), (int, float)) else "", ats="himalayas"))
        except Exception as e: print("warn himalayas", q, e, file=sys.stderr)
    return out

def remotive():
    out = []
    for j in get("https://remotive.com/api/remote-jobs?category=software-dev")["jobs"]:
        l = j["candidate_required_location"]
        if re.search(r"india|worldwide|anywhere|apac|asia", l, re.I):
            out.append(dict(company=j["company_name"], title=j["title"], loc=l, url=j["url"], posted=j["publication_date"][:10], ats="remotive"))
    return out

def hn():
    out = []
    t = get("https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=3")["hits"]
    t = next(h for h in t if "who is hiring" in h["title"].lower())
    for h in get(f"https://hn.algolia.com/api/v1/search?tags=comment,story_{t['objectID']}&query=India&hitsPerPage=200")["hits"]:
        txt = re.sub(r"<[^>]+>", " ", h.get("comment_text") or "")
        first = txt.strip().split("\n")[0][:140]
        if re.search(r"india|bengaluru|bangalore|hyderabad|mumbai", txt[:300], re.I):
            out.append(dict(company=first.split("|")[0].strip(), title=first, loc="see post", url=f"https://news.ycombinator.com/item?id={h['objectID']}", posted=h["created_at"][:10], ats="hn"))
    return out

def main():
    jobs, jobs_lock = [], []
    yc = {"gh": [], "lv": [], "ab": []}
    try: yc = discover_yc()
    except Exception as e: print("warn yc discovery", e, file=sys.stderr)
    tasks = ([(greenhouse, s) for s in dict.fromkeys(GH + yc["gh"])] + [(lever, s) for s in dict.fromkeys(LV + yc["lv"])] + [(ashby, s) for s in dict.fromkeys(AB + yc["ab"])]
             + [(keka, s) for s in KK] + [(freshteam, s) for s in FT] + [(recruitee, s) for s in RC] + [(workday, t) for t in WD])
    with cf.ThreadPoolExecutor(12) as ex:
        futs = {ex.submit(f, s): (f.__name__, s) for f, s in tasks}
        for fu in cf.as_completed(futs):
            try: jobs += [j for j in fu.result() if ok(j["title"], j["loc"])]
            except Exception as e: print("warn", futs[fu], e, file=sys.stderr)
    for s in WK:  # Workable rate-limits bursts (Cloudflare 1015), so one account at a time
        try: jobs += [j for j in workable(s) if ok(j["title"], j["loc"])]
        except Exception as e: print("warn workable", s, e, file=sys.stderr)
        time.sleep(1.5)
    n_board = len(jobs)
    for f in (jooble,):  # broad aggregators: same title + India-city filter as the boards
        try: jobs += [j for j in f() if ok(j["title"], j["loc"])]
        except Exception as e: print("warn", f.__name__, e, file=sys.stderr)
    for f in (himalayas, remotive):
        try: jobs += [j for j in f() if TITLE_OK.search(j["title"]) and not TITLE_BAD.search(j["title"])]
        except Exception as e: print("warn", f.__name__, e, file=sys.stderr)
    for f in (hn, hn_jobs, reddit):  # community posts: no title/city filter beyond their own
        try: jobs += f()
        except Exception as e: print("warn", f.__name__, e, file=sys.stderr)
    # dedupe by url; drop ones already in candidates.json
    known = set()
    try:
        for c in json.load(open(HERE / "candidates.json")):
            known.add((c.get("url") or c.get("apply_url") or "").split("?")[0])
    except Exception: pass
    uniq = {j["url"].split("?")[0]: j for j in jobs}
    cutoff = str(dt.date.today() - dt.timedelta(days=MAX_AGE_DAYS))
    new = [j for u, j in uniq.items() if u not in known and (j["posted"] or "9") >= cutoff]
    new.sort(key=lambda j: j["posted"] or "", reverse=True)  # newest first
    new.sort(key=lambda j: not re.search(r"hyderabad|secunderabad", j["loc"], re.I))  # Hyderabad first (stable)
    out = HERE / "digests"; out.mkdir(exist_ok=True)
    f = out / f"extra_{dt.date.today()}.md"
    f.write_text(f"# Extra sources {dt.date.today()} ({len(new)} jobs)\n\n" + "\n".join(f"- **{j['title']}** — {j['company']} · {j['loc']} · {j['posted']} · {j['ats']}\n  {j['url']}" for j in new) + "\n")
    (HERE / "extra_candidates.json").write_text(json.dumps(new, indent=1))  # read by make_queue.py
    print(f"board-API India matches: {n_board}; total after feeds+dedupe vs candidates.json: {len(new)} -> {f}")
    from collections import Counter; print(Counter(j["ats"] for j in new))

if __name__ == "__main__":
    main()
