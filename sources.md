# Extra India job sources (researched 2026-10-19)

Profile: Ayush Ganvir, ~4.2y, Python/Django/Go/TS/Vue-Nuxt/React, LLM + voice AI. Targets FDE / founding / full-stack / AI engineer, India (Hyderabad > Mumbai > Bengaluru) or remote.
All curl tests used a normal browser User-Agent, no login, no bot-wall bypass. HTTP codes are from today.

## Comparison table

| Source | India AI/backend/FS coverage | Programmatic access (tested) | ToS / scrape risk | Apply friction | In freehire? | Rating |
|---|---|---|---|---|---|---|
| **Direct ATS board APIs** (Greenhouse / Lever / Ashby) | Best signal: the actual AI/voice startups (Sarvam, Cursor, ElevenLabs, Level AI, Certa, Prodigal, DevRev, Observe.ai, TrueFoundry, CRED, Meesho, Zeta ...) | Public JSON, 200: `curl -A UA https://boards-api.greenhouse.io/v1/boards/devrev/jobs` ; `https://api.lever.co/v0/postings/cred?mode=json` ; `https://api.ashbyhq.com/posting-api/job-board/sarvam`. Unknown slug = 404 (Ashby/Lever) | Documented public job-board APIs, intended for this | No account, direct form | Mostly yes (freehire indexes the same boards), but a curated list gives freshness + companies freehire misses | **High** |
| **SmartRecruiters** | Freshworks, Sia etc. | `https://api.smartrecruiters.com/v1/companies/Freshworks/postings?limit=2` -> 200 JSON | Public posting API | Form, usually no account | Yes (Sia seen) | Medium |
| **Workable** | Few India startups | `apply.workable.com/api/v1/widget/accounts/<slug>` returns 200 `{"jobs":[]}` for ANY slug (all my guesses empty) - unreliable | Public widget | No account | Yes | Low |
| **Himalayas** | Remote-worldwide + India-eligible; AI/founding roles (Wise AI, Teamified, Patronus) | `https://himalayas.app/jobs/api?limit=5` and `/jobs/api/search?q=python%20engineer&sort=recent` -> 200 JSON, cursor pagination. Search ignores `country=`, so filter `locationRestrictions` client-side (empty = worldwide, or contains India) | Free API, wants attribution/link back; fine for personal use | Apply links redirect to Himalayas/company; some need Himalayas account | Partially (freehire has `himalayas` source) | Medium |
| **Remotive** | ~12 India/worldwide of 100 software-dev jobs; mostly senior/EU | `https://remotive.com/api/remote-jobs?category=software-dev` -> 200 JSON (`candidate_required_location`) | Public API, asks to link back, rate-limit ~4 calls/day recommended | External ATS / company site | Unknown | Low-Medium |
| **RemoteOK** | Only 1 of 100 mentions India; mostly US-timezone | `https://remoteok.com/api` -> 200 JSON (needs link-back to RemoteOK) | Public API with attribution clause | External | Unknown | Low |
| **WeWorkRemotely** | Few India-eligible | `https://weworkremotely.com/categories/remote-programming-jobs.rss` -> 200 RSS (also `/remote-jobs.rss`) | RSS public | External, no account | Unknown | Low |
| **HN "Who is hiring"** | Small but high quality: ~16 India mentions/month, founder-posted, direct email apply | Algolia: `https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring` then `/search?tags=comment,story_<id>&query=India` -> 200 | Public API | Email founder - no account, good for founding roles | No | Medium (monthly, cheap) |
| **Y Combinator Work at a Startup** | Good (YC cos hiring in India, FDE/founding) | `workatastartup.com/jobs` -> **406** to curl; no public API; needs YC login to apply | Login-gated, skip | Account required | No (freehire lists `workatastartup` as account-type) | Low for automation; Medium manual |
| **Wellfound** | Many India startups | Page 200 but serves Turnstile bot-wall JS; no public API | Prohibits scraping; bot-walled | Account required | Partial | Low (skip) |
| **Instahyre** | Strong India startup list | **403 Cloudflare "Just a moment"** | Bot-walled, skip | Account | No | Low (skip) |
| **startup.jobs** | Decent India AI list (freehire already pulls it) | `/rss` -> **403 Cloudflare** | Bot-walled | Often external ATS; some account | Yes | Covered |
| **Cutshort** | India startups | `cutshort.io/jobs` 200 HTML (Next.js app, no public API) | Scraping not permitted in ToS; login to apply | Account | No | Low |
| **Hirist** | India tech, many agencies | Homepage 200, SPA, no public API | Scrape risk, ToS | Account/OTP | No | Low |
| **Naukri** | Huge, noisy, many body shops | Redirects 301 then SPA/anti-bot (Akamai); no API | Prohibits scraping | Account | No | Low |
| **LinkedIn Jobs** | Largest | Guest endpoint `/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=python&location=India` returned 200 HTML, rate-limits fast | ToS explicitly bans scraping; account bans | Easy Apply needs login | No | Low (do not automate) |
| **Indeed India** | Large | RSS `in.indeed.com/rss` -> 404 (removed); JobSpy needs bot-evasion | Bans scraping | Indeed account | No | Low |
| **Foundit** | Mid | Page 200 HTML SPA, no API | ToS | Account | No | Low |
| **Arc.dev / Welcome to the Jungle** | Remote-global (Arc), mostly Europe (WTTJ) | Pages 200 SPA, no public API | ToS | Account (Arc) | No | Low |
| **JobSpy (speedyapply/JobSpy, `python-jobspy` 1.3.0)** | Scrapes LinkedIn/Indeed/Naukri/Glassdoor | pip package exists; not run (it hits the bot-walled sites above) | Same ToS risk as the sites it scrapes, IP blocks | Same as sites | No | Low (only for lead discovery, not apply) |
| **GitHub awesome lists** | Static company lists: `ghoshsuman845/List-of-Top-Unicorn-Startups-India` (572 stars), `theainerd/MLInterview` (AI startups in India, 541), `avinassh/dev-startups-india` | GitHub search API 200 | None | n/a (find companies, then probe ATS slugs) | n/a | Medium for seeding slug list |
| **Startup funding lists** (Entrackr / Inc42 / Tracxn weekly funding reports) | Lists freshly funded India AI startups = who is about to hire | Manual/RSS (not tested) | Reading fine | n/a | n/a | Medium (weekly manual seed) |

## Honest finding

Direct ATS boards give the cleanest, no-account, programmatically-queryable India jobs, but freehire already indexes most of them. Running the curated-board script today (22 Greenhouse, 7 Lever, 22 Ashby companies, 30-day window, title filter, seniority exclusions) found 130 India title-matches raw, 26 after age filter and removing URLs in candidates.json. Of those only a handful are real new fits (see below); most are Okta/GitLab/Stripe senior or SRE/SET roles. So marginal gain is modest: the value is freshness and company coverage, not volume. The India-only boards (Naukri/Instahyre/Wellfound/Cutshort/LinkedIn/Foundit/Hirist) are walled, ToS-hostile and account-gated; recommend not automating them.

Genuinely new, matching, no-account fits from the run (not in candidates.json):
- AI Agent Engineer - Observe.ai - Hyderabad (Greenhouse, 2026-09-23) https://www.observe.ai/position?gh_jid=5432596008 (company board slug `observeai`)
- AI Engineer - Certa - India remote (Ashby, 2026-10-14) (already in discovery_ai_fullstack.md)
- Forward Deployed Engineer - AI Agents - Prodigal (already applied)
- Forward Deployed Engineer - India - Cursor (known)
- Himalayas: Forward Deployed Engineer (Lexoga, worldwide remote), Sr. Founding Product Engineer (Teamified, India), Full Stack Developer (KOMBO, worldwide), Founding Design Engineer (Substrate) - verify seniority/pay.

## Recommended plan (ranked)

1. **Curated ATS board poller** (`extra_sources.py`, done). Add as step 2 of `daily.py` (run after freehire, write `digests/extra_YYYY-MM-DD.md`, add its slugs to `seen.json`). Grow the slug lists weekly: take company names from the GitHub lists and funding news, then probe `boards-api.greenhouse.io/v1/boards/<slug>/jobs`, `api.lever.co/v0/postings/<slug>`, `api.ashbyhq.com/posting-api/job-board/<slug>` (404 = wrong slug). Verified live slugs are in the script. Apply links are direct no-account forms.
2. **Himalayas search API** (already wired in script). Good for remote/founding roles open to India; filter client-side on empty `locationRestrictions` or India. Use `applicationLink` but prefer finding the company's own ATS page to avoid Himalayas account wall.
3. **HN Who is hiring** (wired, 1 hit this month). Run monthly on the 1st-3rd; email-apply to founders is the best path for founding/FDE roles. Improve by feeding matches to a manual review.
4. **Company-seed discovery** (weekly, manual or small script): GitHub India lists + Entrackr/Inc42 funding roundups -> new slugs for list #1. Highest long-term yield for early-stage AI/voice startups freehire does not index.
5. **Remotive / WWR RSS** as low-priority filler for worldwide-remote roles (script already pulls Remotive; WWR RSS is trivial to add).

Skip: Naukri, LinkedIn, Indeed, Instahyre, Wellfound, Foundit, Hirist, Cutshort, YC WaaS, JobSpy (bot-walled/account-gated/ToS; JobSpy only if the user accepts the risk for discovery).

## Quick-win script

`/Users/ayushganvir/money-maker/jobs/extra_sources.py` (stdlib only). Run: `python3 jobs/extra_sources.py`. Output: `digests/extra_YYYY-MM-DD.md`. Edit `GH`, `LV`, `AB` slug lists, `TITLE_OK`/`TITLE_BAD` regexes, `MAX_AGE_DAYS`. Today's run: 130 raw board matches, 26 fresh (<=30 days) not already in candidates.json (13 Greenhouse, 5 Ashby, 6 Himalayas, 1 Remotive, 1 HN); roughly 6-8 are plausible fits for this profile after dropping Senior/SRE/SET noise (the script keeps "Senior" titles since 4y may qualify).

## Added 2026-10-19 (afternoon)
- `daily.py` now runs `extra_sources.main()` after the freehire digest, so the 08:10 task writes both `digests/<date>.md` and `digests/extra_<date>.md`.
- **Keka** (`<slug>.keka.com/careers/` -> org GUID -> `/careers/api/embedjobs/default/active/<guid>` JSON), **Freshteam** (`<slug>.freshteam.com/jobs` HTML cards), **Recruitee** (`<slug>.recruitee.com/api/offers/`). Slugs = India companies freehire shows on those ATSs (`KK`, `FT`, `RC` in the script).
- **YC slug discovery**: `yc-oss.github.io/api/companies/all.json` -> India + hiring (52) -> probe Greenhouse/Lever/Ashby; cached in `yc_slugs.json`, refreshed every 7 days. Generic-name hits (apollo, raven, cardboard) may be a different company with the same slug; the India-city filter keeps only India roles.
- **Jooble** (`POST jooble.org/api/<key>`, free key): live; key from env `JOOBLE_KEY` or Keychain service `jooble-key`. First test: 160 raw, 51 after India-city filter.
- **Adzuna: not used** (Ayush's decision, 2026-10-19).
- First run: 54 fresh jobs not in candidates.json (was 26): freshteam 17, greenhouse 16, ashby 7, keka 6, himalayas 5, remotive 2, hn 1.
- **Added (same day): Workday, Workable, Reddit, HN job ads**, all free and keyless.
  - Workday: `POST https://<co>.<wdN>.myworkdayjobs.com/wday/cxs/<co>/<site>/jobs` with `{"searchText": q}`; 47 tech companies in `WD`. Lists without login; applying needs a per-company account. First run: 178 India title matches, 98 fresh.
  - Workable: `POST apply.workable.com/api/v3/accounts/<slug>/jobs`; 24 India accounts in `WK` (resolved from freehire apply-link redirects). Cloudflare rate-limits bursts (error 1015), so the script calls one account every 1.5 s.
  - Reddit r/developersIndia: `search.rss?q=hiring` (JSON API is 403 to scripts). Strict title filter; yield is low (0 today).
  - HN job ads: Algolia `tags=job`, kept only when the title names India/an Indian city; rare.
