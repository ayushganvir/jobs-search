#!/usr/bin/env python3
"""Build scored application candidates from freehire (India, last 21 days). Writes candidates.json / candidates.md."""
import json, re, sys, datetime as dt, urllib.parse, urllib.request
from pathlib import Path
HERE = Path(__file__).parent
API = "https://freehire.me/api/v1/jobs/search"
QUERIES = ["ai engineer","llm","generative ai","genai","machine learning engineer","agent","agentic","voice","speech","conversational",
 "forward deployed","solutions engineer","founding engineer","full stack","fullstack","full-stack","backend engineer","backend developer",
 "python","django","software engineer","software developer","senior software engineer","golang","go developer","vue","nuxt","typescript",
 "node","platform engineer","applied ai","ai developer","mcp","rag","product engineer","sde"]
APPLIED = {"prodigal","devrev","emergent","simpplr","backbase","arcesium","certa","truefoundry","village miles","villagemiles","whatfix","weave","cashflo","sia",
 "scrabble","itsacheckmate","cursor","anysphere"}
BAD_CO = re.compile(r"capgemini|cognizant|zensar|pwc|accenture|infosys|wipro|tcs|tata consultancy|hcl|tech mahindra|genpact|deloitte|kpmg|ernst|accellor|bearingpoint|remotestar|jobgether|staffing|consult|infotech|technolog(y|ies) (pvt|private)|hirepro|randstad|adecco|manpower|talent systems|turing|toptal|andela|crossover|lorien|nestack|digitalcube|pando", re.I)
BAD_TITLE = re.compile(r"\b(intern|internship|trainee|fresher|junior|jr\.?|graduate|apprentice|staff|principal|distinguished|vp|vice president|director|head of|manager|architect|lead data|sales|sdr|bdr|account|recruit|marketing|support|customer success|qa|test|sdet|devops|sre|data engineer|data scientist|analyst|designer|ios|android|embedded|firmware|sap|salesforce|mainframe|\.net|java\b|php|ruby|wordpress|dba|security|network|hr\b|finance|legal|content|writer|night shift|contract|fixed.term)\b", re.I)
GOOD_TITLE = [(r"voice|speech|conversational|telephony",10),(r"forward deployed|\bfde\b",9),(r"founding",9),(r"agent|agentic|llm|genai|generative|\brag\b|\bmcp\b",8),
 (r"ai engineer|applied ai|ai developer|ai/ml|ml engineer|machine learning",7),(r"full.?stack",7),(r"backend|back-end|python|django|golang|\bgo\b",6),
 (r"solutions? engineer",5),(r"product engineer|platform engineer|software (engineer|developer)|\bsde\b",5),(r"vue|nuxt|typescript|node|react",3)]
SKILLS = {"python":2,"django":3,"go":2,"golang":2,"vue":2,"nuxt":3,"typescript":1,"react":1,"postgresql":1,"docker":1,"kubernetes":1,"llm":3,"rag":2,"voice":3,"speech":2,"langchain":1,"fastapi":1,"openai":2,"gemini":2}
EASY = {"greenhouse","ashby","lever","freshteam","smartrecruiters","workable","recruitee","comeet","trakstar","bamboohr","jazzhr","teamtailor","rippling","gem","hibob","eightfold"}
CAPTCHA = {"zohorecruit"}; ACCOUNT = {"workday","oracle","icims","taleo","successfactors","radancy","ibm","apple","google","amazon","microsoft","meta","himalayas","startupjobs","startup.jobs","telegram","wellfound","workatastartup","humanbit","linkedin","naukri","oraclecloud","ukg","hrmdirect"}
POS = re.compile(r"\b(python|django|fastapi|flask|golang|go lang|typescript|javascript|node\.?js|react|vue|nuxt|next\.?js|llm|rag|langchain|openai|gemini|generative ai|genai|agentic|ai agents?|voice|speech|asr|tts|postgres(ql)?|docker|kubernetes|rest apis?|microservices)\b", re.I)
NEG = re.compile(r"\b(java|spring boot|\.net|c#|asp\.net|sap|snowflake|etl|power ?bi|tableau|hadoop|mainframe|salesforce|php|ruby|android|ios|kotlin|swift|scala|cobol|abap|workday|oracle ebs|embedded|firmware|selenium|manual testing|devops engineer|data warehouse)\b", re.I)
YRS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years|yrs)", re.I)
def jd_check(j):
    d=re.sub(r"<[^>]+>"," ",j.get("description") or ""); d=re.sub(r"\s+"," ",d)
    if len(d)<200: return True,"short jd"
    pos={m.group(0).lower() for m in POS.finditer(d)}; neg={m.group(0).lower() for m in NEG.finditer(d)}
    yrs=[int(m.group(1)) for m in YRS.finditer(d) if int(m.group(1))<=15]
    if yrs and min(yrs)>=7: return False,"needs %d+ yrs"%min(yrs)
    if len(pos)<2: return False,"few matching skills"
    if len(neg)>len(pos): return False,"stack mismatch: "+",".join(sorted(neg))[:40]
    return True,"%d skills"%len(pos)
def get(p):
    r=urllib.request.Request(API+"?"+urllib.parse.urlencode(p),headers={"User-Agent":"curl/8.7.1","Accept":"application/json"})
    with urllib.request.urlopen(r,timeout=40) as x: return json.load(x)["data"]
def _norm(x):
    return re.sub(r"[^a-z0-9]","",re.sub(r"\b(llc|inc|ltd|labs|pvt|private|limited|technologies|the)\b","",(x or "").lower()))
def attempted():
    urls,cos=set(),set()
    try:
        for l in (HERE/"applied_log.jsonl").read_text().splitlines():
            try: r=json.loads(l)
            except ValueError: continue
            if r.get("url"): urls.add(r["url"].split("?")[0])
            if r.get("status") in ("submitted","confirmed","needs_user","blocked","unconfirmed","interview","rejected"): cos.add(_norm(r.get("company")))
    except OSError: pass
    return urls,cos
ATTEMPTED=attempted
def main():
    a_urls,a_cos=attempted()
    cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=21); found={}
    for q in QUERIES:
        for off in (0,100,200):
            try: rows=get({"q":q,"q_fields":"title","countries":"IN","limit":100,"offset":off})
            except Exception as e: print("warn",q,off,e,file=sys.stderr); break
            for j in rows: found.setdefault(j["public_slug"],j)
            if len(rows)<100: break
    out=[]
    for j in found.values():
        t=j["title"]; co=(j.get("company") or ""); loc=j.get("location") or ""
        if j.get("closed_at") or BAD_TITLE.search(t) or BAD_CO.search(co): continue
        if any(a in co.lower() for a in APPLIED): continue
        if j["url"].split("?")[0] in a_urls or _norm(co) in a_cos: continue
        try:
            if dt.datetime.fromisoformat((j.get("posted_at") or j["created_at"]).replace("Z","+00:00"))<cutoff: continue
        except Exception: pass
        e=j.get("enrichment") or {}; mn=e.get("experience_years_min"); real=j.get("reality") or {}
        if mn is not None and mn>5: continue
        if real.get("fake_freshness") or (real.get("mass_posting_count") or 0)>4: continue
        ok,why=jd_check(j)
        if not ok: continue
        s=0; tl=t.lower()
        for pat,w in GOOD_TITLE:
            if re.search(pat,tl): s=max(s,w)
        if s==0: continue
        sk={x.lower() for x in (j.get("skills") or [])}; s+=min(6,sum(w for k,w in SKILLS.items() if k in sk))
        if mn is not None: s+= 2 if 2<=mn<=4 else (0 if mn<2 else -1)
        hyd=bool(re.search(r"hyderabad|secunderabad",loc+" "+" ".join(j.get("cities") or []),re.I)); remote=bool(re.search(r"remote|anywhere",loc,re.I))
        if hyd: s+=3
        src=j["source"].lower(); kind="easy" if src in EASY else ("captcha" if src in CAPTCHA else ("account" if src in ACCOUNT else "other"))
        out.append({"score":s,"title":t,"company":co,"location":loc,"hyd":hyd,"remote":remote,"exp_min":mn,"posted":(j.get("posted_at") or "")[:10],"source":src,"kind":kind,"url":j["url"].split("?")[0],"slug":j["public_slug"],"jd":why})
    out.sort(key=lambda x:(-x["score"],x["posted"]),reverse=False); out.sort(key=lambda x:-x["score"])
    (HERE/"candidates.json").write_text(json.dumps(out,indent=1))
    from collections import Counter
    print("total",len(out),dict(Counter(o["kind"] for o in out)),"hyd",sum(o["hyd"] for o in out),"remote",sum(o["remote"] for o in out))
    print(dict(Counter(o["source"] for o in out).most_common(14)))
    return out
if __name__=="__main__": main()
