#!/usr/bin/env python3
"""Daily job digest from freehire's public API. Writes jobs/digests/YYYY-MM-DD.md, remembers seen jobs."""
import json, re, sys, datetime as dt, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).parent
API = "https://freehire.me/api/v1/jobs/search"
MAX_AGE_DAYS = 14
QUERIES = ["voice ai", "conversational ai", "forward deployed", "founding engineer",
           "full stack", "ai engineer", "llm engineer", "solutions engineer"]
CITIES = "Bengaluru,Bangalore,Mumbai,Hyderabad"
JUNIOR = re.compile(r"\b(intern|internship|trainee|fresher|junior|jr\.?|associate|graduate)\b", re.I)

NONTECH = re.compile(r"\b(sdr|sales|business development|account executive|recruiter|marketing|customer support)\b", re.I)
CITY_OK = re.compile(r"bengaluru|bangalore|mumbai|navi mumbai|thane|hyderabad|secunderabad", re.I)

def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]

def fetch(q, **extra):
    return get({"q": q, "q_fields": "title", "countries": "IN", "limit": 100, **extra})

def main():
    seen_path = HERE / "seen.json"
    seen = set(json.loads(seen_path.read_text())) if seen_path.exists() else set()
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MAX_AGE_DAYS)
    found = {}
    for q in QUERIES:
        for tag, extra in (("city", {"cities": CITIES}), ("remote", {"work_mode": "remote"})):
            try:
                for j in fetch(q, **extra):
                    j["_tag"] = tag
                    found.setdefault(j["public_slug"], j)
            except Exception as e:
                print(f"warn: {q}/{tag}: {e}", file=sys.stderr)
    fresh = []
    for slug, j in found.items():
        if slug in seen or JUNIOR.search(j["title"]) or NONTECH.search(j["title"]) or j.get("closed_at"):
            continue
        if j["_tag"] == "city" and not CITY_OK.search(j.get("location") or ""):
            continue
        posted = j.get("posted_at") or j.get("created_at")
        try:
            if posted and dt.datetime.fromisoformat(posted.replace("Z", "+00:00")) < cutoff:
                continue
        except ValueError:
            pass
        fresh.append(j)
    fresh.sort(key=lambda j: j.get("posted_at") or "", reverse=True)
    fresh.sort(key=lambda j: not re.search(r"hyderabad|secunderabad", j.get("location") or "", re.I))  # Hyderabad first (stable)
    out = HERE / "digests"; out.mkdir(exist_ok=True)
    f = out / f"{dt.date.today()}.md"
    lines = [f"# Jobs {dt.date.today()} ({len(fresh)} new)\n"]
    for j in fresh:
        lines.append(f"- **{j['title']}** — {j['company']} · {j['location']} · {j['_tag']} · "
                     f"{(j.get('posted_at') or '')[:10]} · {j['source']}\n  {j['url']}")
    if fresh or not f.exists():  # a same-day re-run must not wipe the morning digest
        f.write_text("\n".join(lines) + "\n")
    else:
        with f.open("a") as fh: fh.write(f"\n<!-- re-run {dt.datetime.now():%H:%M}: 0 new -->\n")
    seen_path.write_text(json.dumps(sorted(seen | {j['public_slug'] for j in fresh})))
    print(f"{len(fresh)} new jobs -> {f}")
    try:  # step 2: scored freehire candidates (excludes companies already tried) -> candidates.json
        import build_candidates; build_candidates.main()
    except Exception as e:
        print(f"warn: build_candidates: {e}", file=sys.stderr)
    try:  # step 3: ATS boards / YC slugs / Himalayas / Remotive / HN / Adzuna / Jooble -> digests/extra_<date>.md + extra_candidates.json
        import extra_sources; extra_sources.main()
    except Exception as e:
        print(f"warn: extra_sources: {e}", file=sys.stderr)
    try:  # step 4: merge both into today_queue.json (the apply runs work from it)
        import make_queue; make_queue.main()
    except Exception as e:
        print(f"warn: make_queue: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
