# jobs-search: an agent-driven job-search workflow

A personal system for finding and applying to software jobs in India with Claude agents working in a real Chrome browser:
**sources -> queue -> fill agents -> one status log -> Gmail reconciliation -> live dashboard**.

- **Sources** (`daily.py`, `build_candidates.py`, `extra_sources.py`): freehire API, Greenhouse / Lever / Ashby / Workable /
  Keka / Freshteam / Recruitee boards, ~60 Workday tenants (public cxs JSON), Himalayas, Remotive, HN "Who is hiring", Jooble,
  YC company slug discovery. `make_queue.py` builds one-role-per-company queues by city priority and form friction.
- **Applying**: Claude Code coordinates background agents that fill forms through Control_Chrome (Workday, SuccessFactors,
  Oracle HCM, iCIMS, Greenhouse, Ashby, Zoho...). Walled boards (LinkedIn, Indeed, Wellfound, Naukri) use Claude in Chrome
  prompts (`prompts/`). Humans keep sign-ins, captchas and personal answers.
- **Status**: `joblog.py` is the only writer of `applied_log.jsonl` (validated, newest-wins, one application per company,
  closes finished Chrome tabs). `reconcile.py` turns Gmail receipts/interviews/rejections into status. `chrome_tabs.py`
  lists and cleans job tabs.
- **Dashboard**: `tracker/` (`sync.py` -> `data.json`, `server.py`, `index.html`), optional Cloudflare tunnel (`tracker/tunnel.sh`).
- **Docs**: `PLAYBOOK.md` (every flow), `PORTAL_FILL_GUIDE.md` (per-platform techniques), `sources.md`.

## Setup
1. Python 3.10+, macOS (AppleScript is used for Chrome tab listing/closing), Google Chrome.
2. `cp AGENT_BRIEF.example.md AGENT_BRIEF.md` and fill in your facts and standing answers (kept private by `.gitignore`).
3. Optional keys come from the environment or the macOS Keychain, never from files: `JOOBLE_KEY` / Keychain `jooble-key`;
   Cloudflare token in Keychain for the tunnel.
4. `python3 daily.py` (pull jobs + build queue), `python3 tracker/server.py` (dashboard on 127.0.0.1:8787).
5. Personal data (logs, queues, digests, resumes, filled prompts, Gmail matches) is gitignored by design.

---

# Job hunt ("free hire") — START HERE

If Ayush mentions jobs, applying, resumes, freehire, the tracker, "needs you", Naukri/LinkedIn/Indeed/Wellfound, or anything that hints at this, work from this folder (`~/money-maker/jobs`) and follow this file. Don't re-derive what is written here.

**Status (2026-10-21): applying resumed by hand** (no `PAUSED` file; the `auto-apply-jobs` schedule stays disabled). Create a `PAUSED` file to stop the queue again (`PLAYBOOK.md` §10).

Read next, in this order: `PLAYBOOK.md` (every flow: pipeline, status model, coordinator loop, Chrome tab lifecycle, agents, verification), `AGENT_BRIEF.md` (facts + standing answers), `PORTAL_FILL_GUIDE.md` (per-platform techniques: Workday, SuccessFactors, iCIMS, Greenhouse, ...).

## 1. The goal and the person
- Ayush Ganvir, ~4.2 yrs. Python/Django, Go, TypeScript, Vue/Nuxt, React, LLM + voice AI (Incus voice agents in 20+ hospitals, Flowie BFSI platform, AI agents for 50+ real-estate agencies). Resume: `~/claude_base/resume/` (master `Ayush_Ganvir_Resume.md`).
- Targets: AI/LLM/voice engineer, forward-deployed (FDE), founding engineer, full/backend engineer. **Hyderabad first**, then Mumbai, Bengaluru, remote. India only. Roughly 2-6 yrs, product companies (skip staffing/IT-services, Staff/VP, BI/data-eng, Java/.NET).
- All form facts (CTC, notice period, phone, links, backend story, standing answers) are in **`AGENT_BRIEF.md`** (private, gitignored; copy `AGENT_BRIEF.example.md`). Use only those facts; never invent.

## 2. What lives where
| File / folder | Purpose |
|---|---|
| `PLAYBOOK.md` | Every flow end to end: pipeline, status model, coordinator loop, Chrome tab lifecycle, agent brief template, verification, scheduled tasks, lessons |
| `AGENT_BRIEF.md` | The rules + facts + standing answers every application agent must follow (read it before spawning agents) |
| `PORTAL_FILL_GUIDE.md` | Per-platform fill techniques (Workday first) and what counts as "done" on each |
| `joblog.py` | The only way to write status: `add` (validated, one per company, closes the tab on a final status), `show`, `open`, `check` |
| `chrome_tabs.py` | Chrome tabs via AppleScript: `list`, `cleanup [--dry]` (closes finished/helper/duplicate job tabs only), `close <id>` |
| `prompts/` | Claude-in-Chrome prompts for walled boards: LinkedIn (+ A/B/C parallel splits), Indeed |
| `PAUSED` | Present = applying paused; `make_queue.py` writes an empty queue |
| `applied_log.jsonl` | Source of truth: one JSON line per event (company, title, status, date, ts, note, where, url, channel), written with `joblog.py`. Newest row wins (file order); `superseded` retires a row; skipped rows are kept so we don't retry them |
| `candidates.json`, `build_candidates.py` | Scored India roles from freehire (last 21 days), already-tried ones excluded |
| `today_queue.json`, `make_queue.py`, `batches/` | The apply queue: `make_queue.py` merges `candidates.json` + `extra_candidates.json` (one per company, target cities only, easy forms first, max 30 account portals); runs daily from `daily.py` |
| `daily.py`, `digests/` | Daily freehire digest (scheduled 08:10) |
| `reconcile.py` | Clears "needs you" rows from Gmail confirmations (matches by job number first; a receipt also overrides 'skipped') |
| `resume_link.py` | `on plain|full` serves the resume at a 60-min jobs.ayush.cc link (re-running `on` reuses the live link), `status`, `off` |
| `tabjump.py` | Focus a Chrome tab by id (used by the dashboard's Go-to-tab links) |
| `job_meta.json` | Verified location + work mode (Remote/Hybrid/On-site) per company |
| `tracker/` | Dashboard (`sync.py` builds `data.json`, `index.html` renders, `server.py` on 127.0.0.1:8787, no login). Public: https://jobs.ayush.cc (Cloudflare tunnel) and ngrok |
| `resume_b64.txt`, `Ayush_Ganvir_Resume_plain.pdf` | 7 KB plain-text resume PDF (SHA-256 `4ce9bdea…25d6`) used for file uploads |
| `sources.md`, `extra_sources.py`, `yc_slugs.json` | Which job sources work and which are walled; extra poller (run by `daily.py`); weekly YC slug cache |
| `discovery_*.md` | Earlier ranked shortlists |
| `running.json`, `chrome_sites.json` | What the dashboard's "Running now" / Chrome-sites strips read |
| `tracker/index.html.bak` | Backup of the pre-redesign page |

## 3. How a working session goes
1. Read `tracker/data.json` (or open https://jobs.ayush.cc) for the state; check `applied_log.jsonl` tail.
2. Refresh candidates: `python3 build_candidates.py`. Pick roles with real fit; read the posting before applying.
3. Spawn fill agents in Ayush's Chrome (template in `PLAYBOOK.md` §6; they read `AGENT_BRIEF.md` + `PORTAL_FILL_GUIDE.md` and do not edit files).
4. Verify each agent report on the tab / in Gmail, then log it with `python3 joblog.py add ... --tab <id>` (a final status closes the tab). Anything that needs Ayush stays open, logged `needs_user` with the exact step and its tab id.
5. `python3 chrome_tabs.py cleanup` after each batch. The 10-minute inbox reconciler (`reconcile-job-emails`) keeps statuses honest and also runs the cleanup.

## 4. Hard rules (learned the hard way)
- **No built-in browser, ever.** All form work is in Ayush's real Chrome ("Ayush Ganvir" profile) through the Control_Chrome tools; everything that needs him lives in his Chrome tab group. (He said the built-in browser loses context.)
- **Never** solve captchas / Cloudflare checks, create accounts, sign in, or type passwords/tokens. Leave a filled tab for Ayush. Don't put API tokens anywhere: Cloudflare tokens live in the Keychain via `~/bin/cf` (see global CLAUDE.md).
- Don't guess answers. Genuinely personal answers (EST-hours, zip, last working day, race) are Ayush's; tell him exactly which field.
- Fill every field including optional ones; EEO "decline" unless Ayush told us.
- Keep agents on their own tab IDs; the pane has a tab cap (~10). Don't kill another agent's helper processes.
- **Chrome profile:** Ayush's job accounts are in the "Ayush Ganvir" profile; other profiles hold unrelated work tabs: never read/touch them. Chrome has no tab-grouping tool for me.
- Workday masked date inputs reject scripted typing; fixes are in `PORTAL_FILL_GUIDE.md` §1 (delete/re-add, reload, React-fiber onBlur).
- Gmail: read-only. Search broadly, read bodies, match by job number (JPMorgan was once missed by a narrow query).
- No screenshots unless Ayush asks (a few allowed for visual QA of the dashboard).
- Be honest in summaries: say what is submitted vs only filled; the final status fence is required (global CLAUDE.md).

## 3b. Single source of truth
- `applied_log.jsonl` is the only record. Everything (dashboard Home/Applications/Today, reports) is derived from it by `tracker/sync.py` on every page refresh (the page polls every 10 s). Never hand-edit `data.json`.
- `sync.py` collapses per company: an open row disappears once the same company has a later-or-equal applied row, and duplicate open rows (title spelled differently) keep only the newest. Home "Needs you" and the queue bar count the same list.
- Every status change is logged the moment it happens (submitted / needs_user / skipped), with `joblog.py add`, not at the end.

## 4a. Tab links
- Every 'needs you' row on the dashboard has **Go to tab**: `http://127.0.0.1:8787/go?tab=<chrome tab id>&u=<job url>` (local only; 403 via the tunnel). `tracker/server.py` calls `tabjump.py`, which focuses that Chrome tab by id, else by URL, else opens the URL. `sync.py` finds the tab ids live from Chrome on every refresh. Use the same links in chat replies for anything that needs Ayush.

## 4b. Verify, don't ask
- Never ask Ayush whether something was submitted. Read the open tab (confirmation text, errors like "Incorrect Captcha", form still present) and search Gmail (receipt by job number/company) first. Close tabs confirmed done or dead, log them, and ask only for human-only items (captcha, sign-in, personal answers).
- On every "continue"/progress message: sweep all job tabs + Gmail, run `reconcile.py`, update `applied_log.jsonl`, `tracker/sync.py`, then report what remains.
- One application per company (check `applied_log.jsonl` by company before queuing).

## 5. Known limits
- No-account forms (Greenhouse/Ashby/Lever/Workable/SmartRecruiters/Freshteam) are mostly exhausted for the current freehire pool. What is left: ~38 Zoho forms (image captcha for Ayush), ~200 Workday/Oracle/SuccessFactors roles (per-company accounts), ~115 Telegram posts (manual).
- Walled sites (Naukri, LinkedIn, Wellfound, Instahyre, Indeed): only inside Ayush's own signed-in Chrome profile and at small volume; see `sources.md`.

## 6. Infrastructure
- Dashboard: `tracker/server.py` (restart: `for p in $(lsof -ti :8787); do kill $p; done; cd tracker && nohup python3 server.py >/tmp/claude-501/jobs-server.log 2>&1 &`) · public link down (530): `tracker/tunnel.sh` restarts the tunnel over HTTP/2 (QUIC drops on some networks) · Cloudflare tunnel `jobs-dashboard-ayush` (personal account, id in `~/.cloudflared/jobs-dashboard-ayush.id`) · DNS `jobs.ayush.cc` · ngrok backup.
- Cloudflare accounts via `cf` (`~/bin/cf`, Keychain). Second-Mac installer: `~/money-maker/tools/install-cf.sh`.
- Scheduled: `daily-job-digest` (08:00: daily.py = freehire digest + build_candidates + extra_sources + make_queue), `reconcile-job-emails` (every 10 min 08:00-23:50, reads only new threads via `reconcile.py --known`; also counts LinkedIn "your application was sent" mails from the Claude-in-Chrome LinkedIn agents and Zoho portal invites as submitted, adding rows via `add_if_missing`), `auto-apply-jobs` (10:30 and 16:30; DISABLED while paused). The reconciler also reads Indeed/Wellfound receipts and runs `chrome_tabs.py cleanup`. All run only while the Claude app and Chrome are open.
- Resume upload into Chrome pages: `python3 resume_link.py on plain|full` gives a 60-minute link on jobs.ayush.cc (shared by all agents; `on` again reuses it); fetch it in the page, attach; `off` when no agent is uploading.
- freehire MCP: `freehire-full` (token in the MCP config). Public API: `https://freehire.me/api/v1/jobs/search` (send a curl-like User-Agent).

## 7. Open items (update this list)
See the dashboard Home tab ("Needs you now"). Status snapshot lives in the data, not here.
